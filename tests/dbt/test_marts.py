"""mart_segment_week: grain, reconciliation, generator parity, point-in-time correctness."""
import duckdb
import pandas as pd
import pytest

from generator.config import N_WEEKS
from generator.metrics import contribution_margin_usd
from generator.scenarios import default_scenarios
from generator.simulate import simulate
from generator.io import load_duckdb, write_parquet
from tests.dbt.conftest import SEED, dbt_build, query

N_SEGMENTS = 36
MART = "main.mart_segment_week"
HOMES_COLUMNS = [
    "home_id", "market", "band", "product", "segment", "offer_date", "model_valuation", "spread_pct",
    "reno_estimate_usd", "offer_price", "outcome", "contract_date", "cancel_date", "close_date", "fee_usd",
    "reno_complete_date", "reno_actual_usd", "list_date", "first_buyer_offer_date", "days_to_first_offer",
    "showings", "resale_date", "resale_price", "hold_days", "holding_cost_usd", "selling_cost_usd",
]
DATE_COLUMNS = [c for c in HOMES_COLUMNS if c.endswith("_date")]


@pytest.mark.parametrize("run", ["injected", "control"])
def test_mart_grain_complete(built_runs, run):
    rows, keys = query(built_runs[run], f"""
        select count(*), count(distinct (segment, week)) from {MART}""")[0]
    assert rows == N_SEGMENTS * N_WEEKS
    assert keys == rows


@pytest.mark.parametrize("run", ["injected", "control"])
def test_counts_reconcile(built_runs, run):
    db = built_runs[run]
    offers, resales = query(db, f"select sum(offers), sum(resales) from {MART}")[0]
    raw_offers, raw_resales = query(db, "select count(*), count(resale_date) from raw.homes")[0]
    assert (offers, resales) == (raw_offers, raw_resales)


@pytest.mark.parametrize("run", ["injected", "control"])
def test_cm_parity_with_generator(built_runs, run):
    db = built_runs[run]
    with duckdb.connect(str(db), read_only=True) as con:
        homes = con.execute("select * from raw.homes where resale_date is not null").df()
    expected = contribution_margin_usd(homes).sum()
    (actual,) = query(db, f"select sum(cm_usd) from {MART}")[0]
    assert actual == pytest.approx(expected, rel=1e-6)


def _homes_row(home_id: str, **dates) -> dict:
    row = {c: None for c in HOMES_COLUMNS}
    row.update(home_id=home_id, market="M01", band="B1", product="cash", segment="M01-B1-cash",
               offer_date="2025-01-06", **dates)
    return row


def test_awaiting_offer_point_in_time(tmp_path):
    homes = pd.DataFrame([
        _homes_row("H0", list_date="2025-01-08", first_buyer_offer_date="2025-01-20"),
        _homes_row("H1", list_date="2025-01-14"),
        _homes_row("H2", list_date="2025-01-06", first_buyer_offer_date="2025-02-10"),
    ], columns=HOMES_COLUMNS)
    for col in DATE_COLUMNS:
        homes[col] = pd.to_datetime(homes[col])
    cuts = pd.DataFrame({
        "home_id": ["H0", "H0", "H1"], "cut_number": [1, 2, 1],
        "cut_date": pd.to_datetime(["2025-01-22", "2025-01-29", "2025-01-27"]), "cut_pct": [0.01] * 3,
    })
    db = tmp_path / "radar_fixture.duckdb"
    with duckdb.connect(str(db)) as con:
        con.execute("create schema raw")
        con.register("h", homes)
        con.register("c", cuts)
        con.execute("create table raw.homes as select * from h")
        con.execute("create table raw.price_cuts as select * from c")
    dbt_build(db, "injected", tmp_path)
    rows = query(db, f"""
        select week, awaiting_offer, first_offers, price_cuts from {MART}
        where segment = 'M01-B1-cash' and week < 7 order by week""")
    # H2's first offer is week 5 (Feb 10); H0's is week 2 (Jan 20, not before week 2's start).
    assert rows == [(0, 0, 0, 0), (1, 2, 0, 0), (2, 3, 1, 1), (3, 2, 0, 2), (4, 2, 0, 0),
                    (5, 2, 1, 0), (6, 1, 0, 0)]


def test_no_lookahead(built_runs, tmp_path):
    cutoff = 40
    run_dir = tmp_path / "parquet"
    write_parquet(simulate(SEED, default_scenarios(), cutoff_week=cutoff), run_dir)
    db = tmp_path / "radar_cutoff.duckdb"
    load_duckdb(db, run_dir)
    dbt_build(db, "injected", tmp_path)
    sql = f"select * from {MART} where week < {cutoff} order by segment, week"
    with duckdb.connect(str(db), read_only=True) as con:
        partial = con.execute(sql).df()
    with duckdb.connect(str(built_runs["injected"]), read_only=True) as con:
        full = con.execute(sql).df()
    assert len(full) == N_SEGMENTS * cutoff
    pd.testing.assert_frame_equal(partial, full, check_exact=False, rtol=1e-9)


def test_sample_scale_label_is_true(built_runs):
    (revenue,) = query(built_runs["control"], f"select sum(resale_usd) from {MART} where week between 26 and 77")[0]
    assert 1.4e9 <= revenue <= 1.8e9
