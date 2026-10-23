"""Detector KPIs against ground truth. Only /eval reads ground truth. Synthetic data — not Opendoor data."""

EXPECTED_KIND = {"days_to_first_offer": "demand_softening", "conversion": "adverse_selection",
                 "reno_overrun": "reno_cost_drift"}


def true_pairs(scenarios: list[dict]) -> dict[str, tuple[str, str]]:
    """Scenario name -> (alert kind, scope) the detector should raise for it."""
    out = {}
    for s in scenarios:
        kind = next(EXPECTED_KIND[e] for e in s["effects"] if e in EXPECTED_KIND)
        out[s["scenario"]] = (kind, s["scope"])
    return out


def scenario_kpis(scenario: dict, alert_weeks: list[int]) -> dict:
    """First alert on the true (kind, scope), detection delay vs onset, and lead time vs margin visibility.

    lead_weeks > 0 means the alert came before sold-cohort margin showed the problem.
    """
    first = min(alert_weeks) if alert_weeks else None
    visible = scenario.get("cm_first_visible_week")
    return {
        "first_alert_week": first,
        "start_week": scenario["start_week"],
        "cm_first_visible_week": visible,
        "delay_weeks": None if first is None else first - scenario["start_week"],
        "lead_weeks": None if first is None or visible is None else visible - first,
        "before_cm": first is not None and (visible is None or first < visible),
    }


def false_alert_stats(weekly: dict[int, list[tuple[str, str, str]]], true: set[tuple[str, str]],
                      evaluable: list[int]) -> dict:
    """Alerts on any (kind, scope) not in `true`: distinct episodes (alert IDs) and alert-weeks, per evaluable week."""
    wrong_ids, wrong_weeks = set(), 0
    for week in evaluable:
        for alert_id, kind, scope in weekly.get(week, []):
            if (kind, scope) not in true:
                wrong_ids.add(alert_id)
                wrong_weeks += 1
    n = max(1, len(evaluable))
    return {"wrong_episodes": len(wrong_ids), "wrong_alert_weeks": wrong_weeks, "evaluable_weeks": len(evaluable),
            "wrong_alert_weeks_per_week": wrong_weeks / n, "wrong_episodes_per_week": len(wrong_ids) / n}
