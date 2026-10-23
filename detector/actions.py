"""Deterministic action catalog: kind -> (action template, owner). Templates name scopes, never numbers."""

CATALOG = {
    "adverse_selection": ("Widen spread or add in-person inspection for {scope}; audit model valuation inputs", "Pricing"),
    "demand_softening": ("Slow acquisitions in {scope}; reprice aged listings", "Resale"),
    "reno_cost_drift": ("Re-baseline renovation estimates in {scope}; require in-person assessment", "Renovation"),
    "portfolio_shift": ("Portfolio-wide shift in {metric}; check external drivers", "Analytics"),
}


def action_for(kind: str, scope: str, metric: str) -> tuple[str, str]:
    template, owner = CATALOG[kind]
    return template.format(scope=scope, metric=metric), owner
