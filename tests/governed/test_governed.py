"""Governed query layer: IDs, windows, thresholds, parity with MetricFlow, isolation.

Synthetic data — not Opendoor data. Build connections are closed before a store opens (DuckDB refuses
mixed read-only/read-write connections to one file in a process), and before mf runs.
"""
import json
from datetime import date

import duckdb
import pytest
import yaml

from detector.governed import MIN_DENOMINATOR, DerivedFact, GovernedStore, MetricPanel
from tests.conftest import DBT_PROJECT, query
from tests.dbt.test_semantic import mf_csv, mf_project  # noqa: F401  (fixture reused)

START_DATE = date.fromisoformat(yaml.safe_load((DBT_PROJECT / "dbt_project.yml").read_text())["vars"]["start_date"])


@pytest.fixture
def db(built_runs):
    return str(built_runs["injected"])


@pytest.fixture
def store(db):
    with GovernedStore(db, "injected") as s:
        yield s


def test_query_id_deterministic(db):
    with GovernedStore(db, "injected") as a, GovernedStore(db, "injected") as b:
        pa = a.panel("contract_rate", "market", 50)
        pb = b.panel("contract_rate", "market", 50)
    assert pa.query_id == pb.query_id
    assert pa.query_id.startswith("Q") and len(pa.query_id) == 11
    assert pa.values.equals(pb.values)


def test_query_id_changes_with_as_of_and_window(store):
    base = store.panel("contract_rate", "market", 50, window_weeks=4)
    ids = {
        base.query_id,
        store.panel("contract_rate", "market", 51, window_weeks=4).query_id,
        store.panel("contract_rate", "market", 50, window_weeks=2).query_id,
        store.panel("contract_rate", "band", 50, window_weeks=4).query_id,
        store.panel("first_offer_rate", "market", 50, window_weeks=4).query_id,
    }
    assert len(ids) == 5


def test_query_id_includes_run_id(db):
    with GovernedStore(db, "injected") as a, GovernedStore(db, "other") as b:
        assert a.panel("offers", "portfolio", 10).query_id != b.panel("offers", "portfolio", 10).query_id


def test_window_sums_numerators_and_denominators(built_runs, db):
    expected = query(built_runs["injected"],
                     "select sum(contracts)::double / sum(offers) from main.mart_segment_week where week between 47 and 50")[0][0]
    with GovernedStore(db, "injected") as s:
        panel = s.panel("contract_rate", "portfolio", 50, window_weeks=4)
    row = panel.values[panel.values.week == 50].iloc[0]
    assert row.scope == "portfolio"
    assert row.value == pytest.approx(expected, abs=1e-12)
    assert row.denominator == query(built_runs["injected"],
                                    "select sum(offers) from main.mart_segment_week where week between 47 and 50")[0][0]


def test_derived_metric_uses_windowed_sums(built_runs, db):
    sql = ("select (sum(reno_actual_sum) / sum(reno_estimate_sum) - 1) from main.mart_segment_week "
           "where week between 45 and 50 and market = 'M05'")
    expected = query(built_runs["injected"], sql)[0][0]
    with GovernedStore(db, "injected") as s:
        panel = s.panel("reno_overrun_pct", "market", 50, window_weeks=6)
    row = panel.values[(panel.values.scope == "M05") & (panel.values.week == 50)].iloc[0]
    assert row.value == pytest.approx(expected, abs=1e-12)


def test_below_min_denominator_is_none(store):
    panel = store.panel("contract_rate", "segment", 77, window_weeks=1)
    v = panel.values
    small = v[v.denominator < MIN_DENOMINATOR["contract_rate"]]
    big = v[v.denominator >= MIN_DENOMINATOR["contract_rate"]]
    assert len(small) > 0 and len(big) > 0
    assert all(x is None for x in small.value)
    assert all(x is not None for x in big.value)


def test_levels_and_scopes(store):
    assert set(store.panel("offers", "portfolio", 20).values.scope) == {"portfolio"}
    assert set(store.panel("offers", "band", 20).values.scope) == {"B1", "B2", "B3"}
    assert len(set(store.panel("offers", "market", 20).values.scope)) == 6
    assert len(set(store.panel("offers", "segment", 20).values.scope)) == 36
    assert "M02-B2-cash" in set(store.panel("offers", "segment", 20).values.scope)


def test_non_additive_inventory_takes_last_week_and_sums_scopes(built_runs, db):
    expected = query(built_runs["injected"],
                     "select sum(unsold_inventory_usd) from main.mart_segment_week where week = 30")[0][0]
    with GovernedStore(db, "injected") as s:
        v = s.panel("unsold_inventory_usd", "portfolio", 30, window_weeks=4).values
    assert v[v.week == 30].iloc[0].value == pytest.approx(expected)
    assert v.denominator.isna().all()


def test_start_week_and_as_of_bound_output(store):
    v = store.panel("offers", "market", 30, start_week=20).values
    assert v.week.min() == 20 and v.week.max() == 30


def test_parity_with_metricflow(mf_project, built_runs, tmp_path):  # noqa: F811
    metrics = ["contract_rate", "first_offer_rate", "reno_overrun_pct"]
    rows = {}
    for dim in ("market", "band"):
        rows[dim] = mf_csv(mf_project, built_runs["injected"], "injected", tmp_path, "--metrics", ",".join(metrics),
                           "--group-by", f"metric_time__week,segment_week__{dim}")
    compared = 0
    with GovernedStore(str(built_runs["injected"]), "injected") as s:
        for dim, scope_value in (("market", "M02"), ("band", "B2")):
            header, body = rows[dim][0], rows[dim][1:]
            panels = {m: s.panel(m, dim, 77, window_weeks=1).values for m in metrics}
            for r in body:
                rec = dict(zip(header, r))
                week = (date.fromisoformat(rec["metric_time__week"][:10]) - START_DATE).days // 7
                scope = next(v for k, v in rec.items() if k.endswith(dim))
                if scope != scope_value:
                    continue
                for m in metrics:
                    p = panels[m]
                    mine = p[(p.scope == scope) & (p.week == week)].iloc[0].value
                    if mine is None or rec[m] in ("", "nan", "None"):
                        continue
                    assert float(rec[m]) == pytest.approx(mine, abs=1e-9)
                    compared += 1
    assert compared > 100


def test_store_no_lookahead(db, cutoff_run):
    with GovernedStore(db, "injected") as full, GovernedStore(str(cutoff_run), "injected") as cut:
        for metric in ("contract_rate", "first_offer_rate", "reno_overrun_pct", "contribution_margin_pct"):
            a = full.panel(metric, "market", 39, window_weeks=4).values
            b = cut.panel(metric, "market", 39, window_weeks=4).values
            assert a.week.max() == 39
            # Same facts; only float summation order may differ between two separate builds.
            assert a[["scope", "week", "denominator"]].equals(b[["scope", "week", "denominator"]]), metric
            assert a.value.isna().equals(b.value.isna()), metric
            both = a.value.notna()
            assert a.value[both].astype(float).to_numpy() == pytest.approx(b.value[both].astype(float).to_numpy(), abs=1e-12)


def test_store_is_single_file_read_only(store):
    with pytest.raises(duckdb.Error):
        store._con.execute("create table t as select 1")
    panel = store.panel("contract_rate", "market", 40)
    assert "attach" not in panel.sql.lower()


def test_derived_traces_inputs(store):
    p = store.panel("contract_rate", "portfolio", 40)
    fact_id = store.register_derived("offers last week", 12.0, "count", (p.query_id,), "offers[w40]")
    fact = store.get(fact_id)
    assert isinstance(fact, DerivedFact) and fact_id.startswith("D") and len(fact_id) == 11
    assert fact.inputs == (p.query_id,)
    assert store.get(p.query_id) is p
    assert isinstance(p, MetricPanel)
    assert {x.query_id if isinstance(x, MetricPanel) else x.fact_id for x in store.all()} == {p.query_id, fact_id}
    assert store.register_derived("offers last week", 12.0, "count", (p.query_id,), "offers[w40]") == fact_id
    with pytest.raises(ValueError):
        store.register_derived("bad", 1.0, "count", ("Qnotreal",), "x")
    with pytest.raises(ValueError):
        store.register_derived("bad", 1.0, "furlongs", (p.query_id,), "x")
    with pytest.raises(ValueError):
        store.get("Qnotreal")


def test_rejects_unknown_metric_level_and_run(db, tmp_path, store):
    with pytest.raises(ValueError):
        store.panel("not_a_metric", "market", 10)
    with pytest.raises(ValueError):
        store.panel("offers", "galaxy", 10)
    with pytest.raises(ValueError):
        store.panel("offers", "market", 10, window_weeks=0)
    for bad in ("Injected", "1abc", "a-b", "x; drop", ""):
        with pytest.raises(ValueError):
            GovernedStore(db, bad)
    with pytest.raises(ValueError):
        GovernedStore(str(tmp_path / "missing.duckdb"), "injected")


def test_log_written(db, tmp_path):
    log = tmp_path / "logs" / "queries.jsonl"
    with GovernedStore(db, "injected", log_path=str(log)) as s:
        p = s.panel("contract_rate", "market", 40)
        s.panel("contract_rate", "market", 40)  # cached: not logged twice
        d = s.register_derived("x", 1.0, "ratio", (p.query_id,), "f")
    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert [x["id"] for x in lines] == [p.query_id, d]
    assert lines[0]["metric"] == "contract_rate" and lines[0]["level"] == "market"
    assert lines[0]["window_weeks"] == 4 and lines[0]["as_of_week"] == 40 and lines[0]["sql"] == p.sql
    assert lines[1]["label"] == "x" and lines[1]["formula"] == "f"
