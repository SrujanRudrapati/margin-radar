from dataclasses import replace

import pytest

from generator.ground_truth import compute_ground_truth, first_visible_week
from generator.scenarios import default_scenarios
from generator.simulate import simulate

SEED = 42


@pytest.fixture(scope="module")
def truth():
    return {t["scenario"]: t for t in compute_ground_truth(SEED, default_scenarios())}


def test_one_entry_per_scenario_with_required_keys(truth):
    assert set(truth) == {"A", "B", "C"}
    for t in truth.values():
        assert {
            "scenario", "effects", "scope_type", "scope", "segments", "start_week", "start_date",
            "cm_first_visible_week", "cm_first_visible_date", "cm_lag_weeks",
            "cm_first_visible_week_solo",
        } <= set(t)
        assert t["start_week"] == 30
        assert t["start_date"] == "2025-08-04"


def test_segments_listed(truth):
    assert len(truth["A"]["segments"]) == 6     # 3 bands x 2 products
    assert len(truth["B"]["segments"]) == 12    # 6 markets x 2 products
    assert len(truth["C"]["segments"]) == 6


def test_every_problem_shows_up_in_sold_cohort_margin_later(truth):
    for t in truth.values():
        assert t["cm_first_visible_week"] is not None, t["scenario"]
        assert t["cm_lag_weeks"] == t["cm_first_visible_week"] - t["start_week"]
        assert t["cm_lag_weeks"] > 0


def test_adverse_selection_lag_spans_the_hold_period(truth):
    # Bad purchases only hit margin when they resell (~120-day hold).
    assert truth["B"]["cm_lag_weeks"] >= 8


def test_no_op_injection_never_shows_in_margin():
    c = next(s for s in default_scenarios() if s.name == "C")
    (t,) = compute_ground_truth(SEED, (replace(c, effects={"reno_overrun": 1.0}),))
    assert t["cm_first_visible_week"] is None
    assert t["cm_lag_weeks"] is None


def test_bigger_shock_is_visible_no_later():
    c = next(s for s in default_scenarios() if s.name == "C")
    (base,) = compute_ground_truth(SEED, (c,))
    (big,) = compute_ground_truth(SEED, (replace(c, effects={"reno_overrun": 1.6}),))
    assert big["cm_first_visible_week"] <= base["cm_first_visible_week"]


def test_visible_week_is_measured_on_the_shipped_combined_run(truth):
    # The injected run that ships carries all three scenarios at once, and B's band overlaps A's and
    # C's markets, so the KPI must use the combined run; the solo run is kept for attribution only.
    scenarios = default_scenarios()
    combined, control = simulate(SEED, scenarios).homes, simulate(SEED).homes
    for s in scenarios:
        assert truth[s.name]["cm_first_visible_week"] == first_visible_week(s, combined, control)
        assert truth[s.name]["cm_first_visible_week_solo"] == first_visible_week(s, simulate(SEED, (s,)).homes, control)


def test_single_scenario_combined_equals_solo():
    c = next(s for s in default_scenarios() if s.name == "C")
    (t,) = compute_ground_truth(SEED, (c,))
    assert t["cm_first_visible_week"] == t["cm_first_visible_week_solo"]
