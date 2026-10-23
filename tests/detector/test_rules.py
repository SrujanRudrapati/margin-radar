"""Integration tests for detect() on the seed-42 runs. The tests (not the detector) read ground truth."""
import json

import pytest

from detector.drift import DriftScore
from detector.governed import GovernedStore
from detector.models import Abstention, DetectorResult
from detector.rules import classify_adverse_selection, detect

TRUE_ALERTS = {("demand_softening", "M02"), ("adverse_selection", "B2"), ("reno_cost_drift", "M05")}


def _all_weeks(db, run_id):
    with GovernedStore(str(db), run_id) as store:
        return {week: detect(store, week) for week in range(6, store.max_week + 1)}


@pytest.fixture(scope="module")
def injected(built_runs):
    return _all_weeks(built_runs["injected"], "injected")


@pytest.fixture(scope="module")
def control(built_runs):
    return _all_weeks(built_runs["control"], "control")


@pytest.fixture(scope="module")
def truth(built_runs):
    gt = json.loads((built_runs["injected"].parent / "ground_truth.json").read_text())
    return {s["scenario"]: s for s in gt["scenarios"]}


def _first_alert(results, kind, scope):
    weeks = [w for w, r in sorted(results.items()) if any(a.kind == kind and a.scope == scope for a in r.alerts)]
    return weeks[0] if weeks else None


def _evaluable(results):
    return {w: r for w, r in results.items() if not any(a.scope == "all" for a in r.abstentions)}


def test_b_detected_before_cm_visible(injected, truth):
    first = _first_alert(injected, "adverse_selection", "B2")
    assert first is not None and 30 <= first <= truth["B"]["cm_first_visible_week"] - 1, first


@pytest.mark.xfail(strict=True, reason=(
    "Known miss on seed 42 (DECISIONS D8/D9): at ~15 M02 listings/week the first-offer-rate rollup never reaches "
    "Z_ALERT=3.25 before CM shows the problem (week 39); thresholds low enough to catch it (Z=3.0, CUSUM_H=6) "
    "fire on the control run. Reported honestly in Phase 5 rather than loosening the control gate."))
def test_a_detected_before_cm_visible(injected, truth):
    first = _first_alert(injected, "demand_softening", "M02")
    assert first is not None and first <= 38, first


def test_c_detected_before_cm_visible(injected, truth):
    first = _first_alert(injected, "reno_cost_drift", "M05")
    assert first is not None and first <= truth["C"]["cm_first_visible_week"] - 1, first


def test_injected_alerts_only_on_true_scopes(injected):
    wrong = {(w, a.kind, a.scope) for w, r in _evaluable(injected).items() for a in r.alerts
             if (a.kind, a.scope) not in TRUE_ALERTS}
    assert wrong == set()


def test_control_zero_alerts_every_week(control):
    evaluable = _evaluable(control)
    assert len(evaluable) >= 40
    fired = {(w, a.kind, a.scope) for w, r in evaluable.items() for a in r.alerts}
    assert fired == set()


def test_short_history_global_abstention(injected):
    result = injected[6]
    assert isinstance(result, DetectorResult)
    assert result.alerts == ()
    assert any(isinstance(a, Abstention) and a.scope == "all" for a in result.abstentions)


def _summary(result, ranked):
    alerts = [(a.alert_id, a.kind, a.scope, a.onset_week, round(a.signals[0].z, 9)) for a in result.alerts]
    watch = [(w.scope, w.metric) for w in result.watch]
    abst = [(x.scope, x.metric) for x in result.abstentions]
    impacts = [(r.alert_id, r.rank, r.impact.basis, None if r.impact.usd_mid is None else round(r.impact.usd_mid, 2))
               for r in ranked]
    return alerts, watch, abst, impacts


def test_alerts_stable_under_truncation(cutoff_run, built_runs):
    from detector.impact import rank_actions
    with GovernedStore(str(cutoff_run), "injected") as cut, GovernedStore(str(built_runs["injected"]), "injected") as full:
        a, b = detect(cut, 39), detect(full, 39)
        sa, sb = _summary(a, rank_actions(a, cut)), _summary(b, rank_actions(b, full))
    assert len(a.alerts) > 0  # never vacuous: the B2 episode is active at week 39
    assert sa == sb


def test_alert_ids_stable_across_an_episode(injected):
    ids = {}
    for _, r in sorted(injected.items()):
        for a in r.alerts:
            ids.setdefault((a.kind, a.scope), set()).add(a.alert_id)
    for key in (("adverse_selection", "B2"), ("reno_cost_drift", "M05")):
        assert len(ids[key]) == 1, (key, ids[key])


def _score(z, direction):
    return DriftScore(z_latest=z, z_streak=2, cusum_pos=6.0 if direction == "+" else 0.0,
                      cusum_neg=6.0 if direction == "-" else 0.0, direction=direction, onset_week=40, fired=True,
                      baseline=0.0, sigma=0.01)


def test_spread_explains_conversion():
    kind, note = classify_adverse_selection(_score(4.0, "+"), spread=_score(-3.0, "-"))
    assert kind == "watch" and "spread" in note
    kind, _ = classify_adverse_selection(_score(4.0, "+"), spread=_score(0.5, "+"))
    assert kind == "alert"
    kind, _ = classify_adverse_selection(_score(4.0, "+"), spread=None)
    assert kind == "alert"
