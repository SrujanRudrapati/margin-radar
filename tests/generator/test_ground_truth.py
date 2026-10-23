from dataclasses import replace

import pytest

from generator.ground_truth import compute_ground_truth
from generator.scenarios import default_scenarios

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
