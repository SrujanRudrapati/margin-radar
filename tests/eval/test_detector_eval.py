import pytest

from eval.kpis import EXPECTED_KIND, false_alert_stats, scenario_kpis, true_pairs

TRUTH = [
    {"scenario": "B", "effects": {"conversion": 1.25, "resale_vs_model": 0.97}, "scope": "B2", "start_week": 30,
     "cm_first_visible_week": 45},
    {"scenario": "C", "effects": {"reno_overrun": 1.18}, "scope": "M05", "start_week": 30, "cm_first_visible_week": 46},
]


def test_true_pairs_from_effects():
    assert true_pairs(TRUTH) == {"B": ("adverse_selection", "B2"), "C": ("reno_cost_drift", "M05")}
    assert EXPECTED_KIND["days_to_first_offer"] == "demand_softening"


def test_lead_time_math():
    k = scenario_kpis(TRUTH[0], alert_weeks=[38, 39, 40, 52])
    assert (k["first_alert_week"], k["delay_weeks"], k["lead_weeks"], k["before_cm"]) == (38, 8, 7, True)
    late = scenario_kpis(TRUTH[0], alert_weeks=[46])
    assert late["lead_weeks"] == -1 and late["before_cm"] is False
    missed = scenario_kpis(TRUTH[0], alert_weeks=[])
    assert missed["first_alert_week"] is None and missed["before_cm"] is False and missed["lead_weeks"] is None


def test_wrong_scope_counted():
    weekly = {64: [("Ax", "reno_cost_drift", "B2"), ("Ab", "adverse_selection", "B2")],
              65: [("Ax", "reno_cost_drift", "B2")], 66: []}
    stats = false_alert_stats(weekly, {("adverse_selection", "B2")}, evaluable=[64, 65, 66])
    assert stats["wrong_episodes"] == 1 and stats["wrong_alert_weeks"] == 2
    assert stats["wrong_alert_weeks_per_week"] == pytest.approx(2 / 3)


def test_false_alerts_per_week_math():
    weekly = {w: [] for w in range(40)}
    weekly[12] = [("Aq", "demand_softening", "M04")]
    stats = false_alert_stats(weekly, set(), evaluable=list(range(40)))
    assert stats["wrong_alert_weeks_per_week"] == pytest.approx(0.025)
    assert stats["wrong_episodes_per_week"] == pytest.approx(0.025)


@pytest.mark.slow
def test_report_fields_smoke(tmp_path):
    from eval.detector_eval import run_detector_eval
    report = run_detector_eval(seeds=[1, 2], root=tmp_path, tuning_seeds=[1], seen_seeds=[], holdout_seeds=[2])
    assert {"per_seed", "by_split", "gates"} <= set(report)
    for split in ("tuning", "holdout"):
        s = report["by_split"][split]
        assert {"control_alert_weeks", "control_false_alerts_per_week", "wrong_episodes", "precision",
                "recall_before_cm", "scenarios"} <= set(s)
    assert {f"holdout_{gate}" for gate in ("control_zero_alerts", "recall_before_cm", "wrong_alerts")} == set(report["gates"])


def test_fixed_design_seeds_use_generator_defaults():
    from eval.detector_eval import scenario_args
    assert scenario_args(1) == {} and scenario_args(10) == {}


def test_true_holdout_seeds_draw_scopes_and_onsets():
    from eval.detector_eval import CONFIRM_SEEDS, ONSET_WEEK_RANGE, TRUE_HOLDOUT_SEEDS, scenario_args
    from generator.config import BANDS, MARKETS
    assert TRUE_HOLDOUT_SEEDS == tuple(range(11, 21)) and CONFIRM_SEEDS == tuple(range(21, 31))
    draws = [scenario_args(s) for s in TRUE_HOLDOUT_SEEDS + CONFIRM_SEEDS]
    assert draws == [scenario_args(s) for s in TRUE_HOLDOUT_SEEDS + CONFIRM_SEEDS]  # deterministic per seed
    lo, hi = ONSET_WEEK_RANGE
    for d in draws:
        assert d["a_market"] in MARKETS and d["c_market"] in MARKETS and d["a_market"] != d["c_market"]
        assert d["b_band"] in BANDS
        assert all(lo <= d[k] <= hi for k in ("a_start_week", "b_start_week", "c_start_week"))
    assert len({(d["a_market"], d["b_band"], d["c_market"]) for d in draws}) > 1
    assert len({d["b_start_week"] for d in draws}) > 1


def test_generator_cli_args_from_draw():
    from eval.detector_eval import generator_cli_args
    assert generator_cli_args({}) == []
    assert generator_cli_args({"a_market": "M01", "b_start_week": 33}) == ["--a-market", "M01", "--b-start-week", "33"]


def _fake_seed(seed: int) -> dict:
    truth = [{"scenario": "C", "effects": {"reno_overrun": 1.18}, "scope": "M05", "start_week": 30,
              "cm_first_visible_week": 46}]
    runs = {"injected": {"evaluable": [40], "alerts": {"40": [["Ac", "reno_cost_drift", "M05"]]}},
            "control": {"evaluable": [40], "alerts": {}}}
    return {"seed": seed, "truth": truth, "runs": runs}


def test_gates_are_scored_on_the_true_holdout_only():
    from eval.detector_eval import assemble
    report = assemble([_fake_seed(s) for s in (1, 6, 11, 12, 21)], tuning_seeds=[1], seen_seeds=[6],
                      holdout_seeds=[11, 12], confirm_seeds=[21])
    assert list(report["by_split"]) == ["holdout", "tuning", "seen", "confirm"]
    assert report["by_split"]["holdout"]["seeds"] == [11, 12]
    assert set(report["gates"]) == {"holdout_control_zero_alerts", "holdout_recall_before_cm", "holdout_wrong_alerts"}
    assert report["gates"]["holdout_recall_before_cm"]["value"] == {"C": "2/2"}
    assert [r["seed"] for r in report["per_seed"]] == [1, 6, 11, 12, 21]


def test_assemble_needs_holdout_seeds():
    from eval.detector_eval import assemble
    with pytest.raises(ValueError, match="holdout"):
        assemble([_fake_seed(1)], tuning_seeds=[1], seen_seeds=[], holdout_seeds=[])
