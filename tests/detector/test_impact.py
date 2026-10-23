import json
import math

import pytest

from common.banner import SYNTHETIC_BANNER
from common.business import SAMPLE_SCALE_LABEL
from detector.__main__ import main
from detector.governed import GovernedStore
from detector.impact import (
    Impact, RankedAction, compute_impact, confirmed_by_resales, measured, rank, scenario_estimate,
)
from detector.models import Alert, Signal
from detector.rules import detect


def _impact(basis, usd_mid, per100=1000.0):
    return Impact(basis=basis, usd_low=usd_mid, usd_mid=usd_mid, usd_high=usd_mid, scope_bps_low=1.0,
                  scope_bps_mid=1.0, scope_bps_high=1.0, portfolio_cm_bps_low=0.1, portfolio_cm_bps_mid=0.1,
                  portfolio_cm_bps_high=0.1, usd_per_100bps=per100, exposure_usd=per100 * 100,
                  label=SAMPLE_SCALE_LABEL, status="", ref_ids=("Dx",))


def _alert(alert_id, kind="reno_cost_drift", scope="M05", onset=40):
    sig = Signal("reno_overrun_pct", "market", scope, "+", 4.0, 0.1, onset, ("Qx",))
    return Alert(alert_id, kind, "market", scope, onset, (sig,), ())


def test_adverse_selection_scenario_range():
    est = scenario_estimate(exposed_homes=100, avg_price=400_000, excess_share=0.2, portfolio_share=0.5)
    assert (est["usd_low"], est["usd_mid"], est["usd_high"]) == pytest.approx((80_000, 160_000, 240_000))
    assert (est["scope_bps_low"], est["scope_bps_mid"], est["scope_bps_high"]) == pytest.approx((20, 40, 60))
    assert est["portfolio_cm_bps_mid"] == pytest.approx(20)
    assert est["basis"] == "scenario_estimate"
    assert est["label"].startswith("scenario estimate, sample-scale")
    assert est["status"] == "unconfirmed until resales"


def test_impact_formula_hand_fixture():
    m = measured(scope_bps=50, exposure_usd=2_000_000, portfolio_share=0.25)
    assert m["usd_mid"] == pytest.approx(10_000) and m["usd_low"] == m["usd_high"] == m["usd_mid"]
    assert m["portfolio_cm_bps_mid"] == pytest.approx(12.5)
    assert m["usd_per_100bps"] == pytest.approx(20_000)


def test_ranking_sorted_by_rank_key():
    ranked = rank([(_alert("A1"), _impact("measured", 5_000)), (_alert("A2"), _impact("measured", 50_000)),
                   (_alert("A3", kind="portfolio_shift"), _impact("sensitivity", None, per100=20_000))])
    assert [r.alert_id for r in ranked] == ["A2", "A3", "A1"]
    assert [r.rank for r in ranked] == [1, 2, 3]
    assert all(isinstance(r, RankedAction) and r.action and r.owner for r in ranked)


def test_adverse_selection_ranks_on_midpoint():
    est = _impact("scenario_estimate", 160_000)
    ranked = rank([(_alert("Asmall"), _impact("measured", 100_000)), (_alert("Aas", "adverse_selection", "B2"), est),
                   (_alert("Abig"), _impact("measured", 500_000))])
    assert [r.alert_id for r in ranked] == ["Abig", "Aas", "Asmall"]


def test_confirmed_by_resales_rule():
    assert not confirmed_by_resales(weeks_since_onset=10, avg_hold_weeks=16, cohort_resales=50, min_resales=10)
    assert not confirmed_by_resales(weeks_since_onset=20, avg_hold_weeks=16, cohort_resales=5, min_resales=10)
    assert confirmed_by_resales(weeks_since_onset=20, avg_hold_weeks=16, cohort_resales=12, min_resales=10)


@pytest.fixture(scope="module")
def store(built_runs):
    with GovernedStore(str(built_runs["injected"]), "injected") as s:
        yield s


def _first_b2(store):
    for week in range(30, 45):
        result = detect(store, week)
        for a in result.alerts:
            if (a.kind, a.scope) == ("adverse_selection", "B2"):
                return week, a
    pytest.fail("no B2 adverse_selection alert")


def test_b2_first_alert_has_scenario_estimate(store):
    week, alert = _first_b2(store)
    impact = compute_impact(store, alert, week)
    assert impact.basis == "scenario_estimate" and impact.status == "unconfirmed until resales"
    assert impact.usd_mid > 0 and impact.usd_low < impact.usd_mid < impact.usd_high


def test_adverse_selection_switches_to_measured_after_resales(store):
    _, alert = _first_b2(store)
    impact = compute_impact(store, alert, 70)
    assert impact.basis == "measured" and impact.status == "confirmed by resales"


def test_every_impact_number_has_ref_id(store):
    week, alert = _first_b2(store)
    impact = compute_impact(store, alert, week)
    assert impact.ref_ids
    for ref in impact.ref_ids:
        store.get(ref)  # raises if unknown


def test_impact_in_usd_and_bps(store):
    for week in (40, 45):
        for a in detect(store, week).alerts:
            impact = compute_impact(store, a, week)
            if impact.basis in ("measured", "scenario_estimate"):
                assert math.isfinite(impact.usd_mid) and math.isfinite(impact.portfolio_cm_bps_mid)


def test_cli_writes_outputs_with_banner_and_sample_label(built_runs, tmp_path):
    main(["--db", str(built_runs["injected"]), "--run-id", "injected", "--as-of-week", "40", "--out", str(tmp_path)])
    out = tmp_path / "injected" / "week_40"
    payload = json.loads((out / "alerts.json").read_text())
    assert payload["banner"] == SYNTHETIC_BANNER
    assert payload["sample_scale_label"] == SAMPLE_SCALE_LABEL
    assert payload["as_of_week"] == 40 and payload["ranked_actions"]
    assert (out / "queries.jsonl").read_text().strip()
    assert "9,000,000,000" not in (out / "alerts.json").read_text()
