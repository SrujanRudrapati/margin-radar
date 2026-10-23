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
    report = run_detector_eval(seeds=[1, 2], root=tmp_path, tuning_seeds=[1], holdout_seeds=[2])
    assert {"per_seed", "by_split", "gates"} <= set(report)
    for split in ("tuning", "holdout", "all"):
        s = report["by_split"][split]
        assert {"control_alert_weeks", "control_false_alerts_per_week", "wrong_episodes", "precision",
                "recall_before_cm", "scenarios"} <= set(s)
    assert {"control_zero_alerts", "recall_before_cm", "wrong_alerts_max_2"} <= set(report["gates"])
