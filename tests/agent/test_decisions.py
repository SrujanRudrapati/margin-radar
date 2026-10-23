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
