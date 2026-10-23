"""Decision log (DuckDB) and the decision scorer. Synthetic data — not Opendoor data."""
import pytest

from agent.decisions import DecisionLog, savings_usd, score_decisions, seed_examples
from detector.governed import GovernedStore


def test_record_and_list(tmp_path):
    log = DecisionLog(tmp_path / "decisions.duckdb")
    log.record("Aabc", "acted", "widened spread", decided_week=40, scope="B2", kind="adverse_selection")
    log.record("Adef", "deferred", "waiting for resales", decided_week=41, scope="M05", kind="reno_cost_drift")
    rows = log.list()
    assert [r["decision"] for r in rows] == ["acted", "deferred"]
    assert log.list(decision="acted")[0]["alert_id"] == "Aabc"
    assert log.list(kind="reno_cost_drift")[0]["scope"] == "M05"


@pytest.mark.parametrize("bad", [
    dict(decision="ignored"), dict(reason="x" * 501), dict(decided_week=-1), dict(alert_id="drop table"),
])
def test_record_validates(tmp_path, bad):
    log = DecisionLog(tmp_path / "d.duckdb")
    args = dict(alert_id="Aabc", decision="acted", reason="ok", decided_week=40, scope="B2", kind="adverse_selection")
    with pytest.raises(ValueError):
        log.record(**{**args, **bad})


def test_savings_math():
    # 120 bps erosion on $10M of purchases avoided -> $120K
    assert savings_usd(erosion_bps=120, avoided_purchases_usd=10_000_000) == pytest.approx(120_000)
    assert savings_usd(erosion_bps=-30, avoided_purchases_usd=10_000_000) == 0.0  # no realized erosion, no savings


def test_seed_and_score_on_seed42(built_runs, tmp_path):
    log = DecisionLog(tmp_path / "decisions.duckdb")
    with GovernedStore(str(built_runs["injected"]), "injected") as store:
        seeded = seed_examples(log, store)
        assert len(seeded) >= 3 and {d["decision"] for d in seeded} >= {"acted", "deferred"}
        report = score_decisions(log, store)
    assert report["decisions"] == len(seeded)
    assert 0 < report["decisions_influenced"] <= report["alerts_with_decisions"]
    assert report["label"].startswith("estimated $ saved (sample-scale")
    acted = [r for r in report["rows"] if r["decision"] == "acted"]
    assert acted and all(r["estimated_saved_usd"] >= 0 for r in acted)
    assert all(r["realized_erosion_bps"] is None or isinstance(r["realized_erosion_bps"], float) for r in report["rows"])


def test_cli_seed_list_score(built_runs, tmp_path, capsys):
    import json
    from agent.__main__ import main
    log = str(tmp_path / "decisions.duckdb")
    assert main(["decisions", "seed", "--db", str(built_runs["injected"]), "--log", log]) == 0
    assert main(["decisions", "score", "--db", str(built_runs["injected"]), "--log", log]) == 0
    report = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert report["decisions"] >= 3 and "sample-scale" in report["label"]


# --- Phase 6 review findings ---------------------------------------------------------------------------------
import pandas as pd

from agent.decisions import log_decision, visible_week


def test_visible_week_needs_consecutive_weeks_and_reindexes():
    gap = pd.Series({40: -0.001, 41: -0.006, 42: -0.007, 43: -0.009})
    assert visible_week(gap) == 41
    holes = pd.Series({40: -0.006, 42: -0.006, 44: 0.0})  # weeks 41/43 missing: not consecutive
    assert visible_week(holes) is None
    assert visible_week(pd.Series(dtype=float)) is None


@pytest.fixture(scope="module")
def scored(built_runs, tmp_path_factory):
    log = DecisionLog(tmp_path_factory.mktemp("dec") / "decisions.duckdb")
    with GovernedStore(str(built_runs["injected"]), "injected") as store:
        seeded = seed_examples(log, store)
        b2 = next(d for d in seeded if d["scope"] == "B2")
        log_decision(log, store, b2["alert_id"], "acted", "clicked twice", b2["decided_week"] + 1)  # duplicate act
        log.record("Auser01", "dismissed", "user note", 50, "M05", "reno_cost_drift")  # not an example
        report = score_decisions(log, store)
        refs = {r["decision"] + r["scope"]: [store.get(i) for i in r["ref_ids"]] for r in report["rows"]}
        seed_examples(log, store)  # idempotent, keeps user rows
        remaining = log.list()
    return report, refs, remaining


def test_one_acted_decision_per_alert_counts(scored):
    report, _, _ = scored
    acted_b2 = [r for r in report["rows"] if r["decision"] == "acted" and r["scope"] == "B2"]
    assert len(acted_b2) == 2 and sum(r["counted"] for r in acted_b2) == 1
    assert report["estimated_saved_usd"] == pytest.approx(sum(r["estimated_saved_usd"] for r in report["rows"] if r["counted"]))
    assert acted_b2[0]["estimated_saved_usd"] > 0


def test_deferred_and_dismissed_save_nothing(scored):
    report, _, _ = scored
    assert all(r["estimated_saved_usd"] == 0 for r in report["rows"] if r["decision"] != "acted")


def test_saved_fact_cites_purchases_and_erosion(scored):
    _, refs, _ = scored
    facts = refs["actedB2"]
    saved = next(f for f in facts if f.label.endswith("estimated saved usd"))
    cited = {getattr(f, "fact_id", None) for f in facts}
    assert set(saved.inputs) <= cited | {f.query_id for f in facts if hasattr(f, "query_id")}
    purchases = next(f for f in facts if f.label.endswith("avoided purchases usd"))
    assert any("acquisition_usd" in str(i) or i.startswith("Q") for i in purchases.inputs)


def test_seeding_is_idempotent_and_keeps_user_rows(scored):
    _, _, remaining = scored
    assert any(r["alert_id"] == "Auser01" for r in remaining)
    assert sum(1 for r in remaining if r["is_example"]) == 3


def test_log_decision_validates_against_the_alert(built_runs, tmp_path):
    log = DecisionLog(tmp_path / "d.duckdb")
    with GovernedStore(str(built_runs["injected"]), "injected") as store:
        alert_id = next(d["alert_id"] for d in seed_examples(DecisionLog(tmp_path / "s.duckdb"), store) if d["scope"] == "B2")
        with pytest.raises(ValueError):
            log_decision(log, store, alert_id, "acted", "too early", 5)        # before the alert existed
        with pytest.raises(ValueError):
            log_decision(log, store, alert_id, "acted", "too late", 999)       # after the data
        with pytest.raises(ValueError):
            log_decision(log, store, "Anotreal1", "acted", "unknown alert", 40)
        row = log_decision(log, store, alert_id, "acted", "ok", 40)
    assert (row["scope"], row["kind"]) == ("B2", "adverse_selection")


def test_label_states_the_counterfactual_assumption(scored):
    report, _, _ = scored
    assert "does not react to decisions" in report["label"]
