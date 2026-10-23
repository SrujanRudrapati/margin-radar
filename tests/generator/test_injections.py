"""Each injection changes only its own scope, from its start week, by its stated amount.

Control and injected runs share every random draw, so homes outside an injection's
scope must be byte-identical between the two runs.
"""
import pandas as pd
import pytest

from generator.config import START_DATE
from generator.scenarios import Scenario, default_scenarios
from generator.simulate import simulate

SEED = 42


def _week(dates: pd.Series) -> pd.Series:
    return (dates - pd.Timestamp(START_DATE)).dt.days // 7


def _only(name: str) -> tuple[Scenario, ...]:
    return tuple(s for s in default_scenarios() if s.name == name)


@pytest.fixture(scope="module")
def run_a():
    return simulate(SEED, _only("A"))


@pytest.fixture(scope="module")
def run_b():
    return simulate(SEED, _only("B"))


@pytest.fixture(scope="module")
def run_c():
    return simulate(SEED, _only("C"))


def _assert_identical(inj, ctl, mask):
    a = inj.homes[mask(inj.homes)].reset_index(drop=True)
    b = ctl.homes[mask(ctl.homes)].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)


def test_default_scenarios():
    by_name = {s.name: s for s in default_scenarios()}
    assert set(by_name) == {"A", "B", "C"}
    assert (by_name["A"].scope_type, by_name["A"].start_week) == ("market", 30)
    assert by_name["A"].effects == {"days_to_first_offer": 1.40}
    assert by_name["B"].scope_type == "band"
    assert by_name["B"].effects == {"conversion": 1.25, "resale_vs_model": 0.97}
    assert by_name["C"].scope_type == "market"
    assert by_name["C"].effects == {"reno_overrun": 1.18}
    assert by_name["A"].scope != by_name["C"].scope


# --- A: one market, days to first offer +40% from week 30 -------------------

def test_a_days_to_first_offer_up_40pct(run_a, control):
    a = _only("A")[0]
    key = ["home_id"]
    cols = key + ["market", "list_date", "days_to_first_offer"]
    both = run_a.homes[cols].merge(control.homes[cols], on=key, suffixes=("_i", "_c")).dropna()
    hit = both[(both["market_c"] == a.scope) & (_week(both["list_date_c"]) >= a.start_week)]
    assert len(hit) > 100
    ratio = (hit["days_to_first_offer_i"] / hit["days_to_first_offer_c"]).mean()
    assert 1.38 <= ratio <= 1.42


def test_a_leaves_everything_else_identical(run_a, control):
    a = _only("A")[0]
    _assert_identical(run_a, control, lambda h: h["market"] != a.scope)
    _assert_identical(
        run_a, control,
        lambda h: (h["market"] == a.scope) & ~(_week(h["list_date"]) >= a.start_week),
    )


# --- B: one band, conversion +25% at unchanged spread; resale 3% below model --

def test_b_conversion_up_25pct_at_unchanged_spread(run_b, control):
    b = _only("B")[0]

    def contract_rate(h):
        hit = h[(h["band"] == b.scope) & (h["offer_week"] >= b.start_week)]
        return hit["contract_date"].notna().mean()

    assert 1.20 <= contract_rate(run_b.homes) / contract_rate(control.homes) <= 1.30
    pd.testing.assert_series_equal(run_b.homes["spread_pct"], control.homes["spread_pct"])


def test_b_resale_3pct_below_model(run_b, control):
    b = _only("B")[0]
    cols = ["home_id", "band", "offer_week", "resale_price", "model_valuation"]
    both = run_b.homes[cols].merge(control.homes[cols], on=["home_id"], suffixes=("_i", "_c")).dropna()
    hit = both[(both["band_c"] == b.scope) & (both["offer_week_c"] >= b.start_week)]
    assert len(hit) > 100
    ratio = (hit["resale_price_i"] / hit["resale_price_c"]).mean()
    assert ratio == pytest.approx(0.97, abs=0.005)


def test_b_leaves_everything_else_identical(run_b, control):
    b = _only("B")[0]
    _assert_identical(run_b, control, lambda h: h["band"] != b.scope)
    _assert_identical(
        run_b, control, lambda h: (h["band"] == b.scope) & (h["offer_week"] < b.start_week)
    )


# --- C: one market, renovation overrun +18% ---------------------------------

def test_c_reno_overrun_up_18pct(run_c, control):
    c = _only("C")[0]
    cols = ["home_id", "market", "reno_start_date", "reno_actual_usd"]
    both = run_c.homes[cols].merge(control.homes[cols], on=["home_id"], suffixes=("_i", "_c")).dropna()
    hit = both[(both["market_c"] == c.scope) & (_week(both["reno_start_date_c"]) >= c.start_week)]
    assert len(hit) > 100
    ratio = (hit["reno_actual_usd_i"] / hit["reno_actual_usd_c"]).mean()
    assert ratio == pytest.approx(1.18, abs=0.005)


def test_c_leaves_everything_else_identical(run_c, control):
    c = _only("C")[0]
    _assert_identical(run_c, control, lambda h: h["market"] != c.scope)
    _assert_identical(
        run_c, control,
        lambda h: (h["market"] == c.scope) & ~(_week(h["reno_start_date"]) >= c.start_week),
    )


def test_combined_run_leaves_unscoped_homes_identical(injected, control):
    a, b, c = (_only(n)[0] for n in "ABC")
    untouched = lambda h: (h["market"] != a.scope) & (h["market"] != c.scope) & (h["band"] != b.scope)
    _assert_identical(injected, control, untouched)


def test_effects_stack_in_overlapping_segments(injected, control):
    a, b = _only("A")[0], _only("B")[0]
    overlap = lambda h: (h["market"] == a.scope) & (h["band"] == b.scope) & (h["offer_week"] >= b.start_week)  # noqa: E731
    rate = lambda h: h[overlap(h)]["contract_date"].notna().mean()  # noqa: E731
    assert 1.15 <= rate(injected.homes) / rate(control.homes) <= 1.35
    cols = ["home_id", "market", "band", "list_date", "days_to_first_offer"]
    both = injected.homes[cols].merge(control.homes[cols], on="home_id", suffixes=("_i", "_c")).dropna()
    hit = both[(both["market_c"] == a.scope) & (both["band_c"] == b.scope) & (_week(both["list_date_c"]) >= a.start_week)]
    assert len(hit) > 20
    assert 1.36 <= (hit["days_to_first_offer_i"] / hit["days_to_first_offer_c"]).mean() <= 1.44
