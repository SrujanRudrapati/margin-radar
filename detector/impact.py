"""Impact of an alert in sample-scale $ and bps of contribution margin, and ranking.

Synthetic data — not Opendoor data. Dollars are sample-scale (the synthetic portfolio's ~$1.6B/yr) and
never scaled to a company run rate. Every number is registered as a derived fact citing its inputs.
"""
import math
from dataclasses import dataclass
from typing import Literal

from common.business import SAMPLE_SCALE_LABEL
from detector.actions import action_for
from detector.config import (
    ADVERSE_SELECTION_SHORTFALL, FORWARD_WEEKS, IMPACT_TRAILING_WEEKS, MIN_SEGMENT_SAMPLE, WINDOW_WEEKS,
)
from detector.governed import DEFAULT_MIN_DENOMINATOR, MIN_DENOMINATOR, GovernedStore
from detector.models import Alert
from detector.peers import peer_residuals, rollup

Basis = Literal["measured", "scenario_estimate", "sensitivity"]
SCENARIO_PREFIX = "scenario estimate, "


@dataclass(frozen=True)
class Impact:
    basis: Basis
    usd_low: float | None
    usd_mid: float | None
    usd_high: float | None
    scope_bps_low: float | None
    scope_bps_mid: float | None
    scope_bps_high: float | None
    portfolio_cm_bps_low: float | None
    portfolio_cm_bps_mid: float | None
    portfolio_cm_bps_high: float | None
    usd_per_100bps: float | None
    exposure_usd: float | None
    label: str
    status: str
    ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class RankedAction:
    rank: int
    alert_id: str
    kind: str
    scope: str
    impact: Impact
    action: str
    owner: str


def scenario_estimate(exposed_homes: float, avg_price: float, excess_share: float, portfolio_share: float) -> dict:
    exposure = exposed_homes * avg_price
    out = {"basis": "scenario_estimate", "label": SCENARIO_PREFIX + SAMPLE_SCALE_LABEL,
           "status": "unconfirmed until resales", "exposure_usd": exposure, "usd_per_100bps": exposure / 100}
    for name, shortfall in zip(("low", "mid", "high"), ADVERSE_SELECTION_SHORTFALL):
        out[f"usd_{name}"] = exposure * shortfall * excess_share
        out[f"scope_bps_{name}"] = shortfall * excess_share * 1e4
        out[f"portfolio_cm_bps_{name}"] = out[f"scope_bps_{name}"] * portfolio_share
    return out


def measured(scope_bps: float, exposure_usd: float, portfolio_share: float, status: str = "measured") -> dict:
    usd = scope_bps / 1e4 * exposure_usd
    out = {"basis": "measured", "label": SAMPLE_SCALE_LABEL, "status": status, "exposure_usd": exposure_usd,
           "usd_per_100bps": exposure_usd / 100}
    for name in ("low", "mid", "high"):
        out[f"usd_{name}"], out[f"scope_bps_{name}"] = usd, scope_bps
        out[f"portfolio_cm_bps_{name}"] = scope_bps * portfolio_share
    return out


def sensitivity(exposure_usd: float | None) -> dict:
    status = "unquantified; sensitivity only" if exposure_usd is not None else "insufficient data for exposure"
    out = {"basis": "sensitivity", "label": SAMPLE_SCALE_LABEL, "status": status, "exposure_usd": exposure_usd,
           "usd_per_100bps": None if exposure_usd is None else exposure_usd / 100}
    for name in ("low", "mid", "high"):
        out[f"usd_{name}"] = out[f"scope_bps_{name}"] = out[f"portfolio_cm_bps_{name}"] = None
    return out


def confirmed_by_resales(weeks_since_onset: float, avg_hold_weeks: float, cohort_resales: float, min_resales: int) -> bool:
    return weeks_since_onset >= avg_hold_weeks and cohort_resales >= min_resales


def exposed_homes(closes_since_onset: float, cohort_resales: float, forward_closes: float) -> float:
    """Homes bought since onset that are still unsold, plus the next FORWARD_WEEKS of purchases.

    Only resales of the post-onset cohort (weeks >= onset + average hold) reduce it; resales of homes bought
    before onset belong to earlier cohorts.
    """
    return max(0.0, closes_since_onset - cohort_resales) + forward_closes


def rank_key(impact: Impact) -> float:
    if impact.basis == "sensitivity":
        return impact.usd_per_100bps or 0.0
    return impact.usd_mid or 0.0


def rank(items: list[tuple[Alert, Impact]]) -> tuple[RankedAction, ...]:
    ordered = sorted(items, key=lambda pair: (-rank_key(pair[1]), pair[0].alert_id))
    out = []
    for position, (alert, impact) in enumerate(ordered, start=1):
        action, owner = action_for(alert.kind, alert.scope, alert.signals[0].metric)
        out.append(RankedAction(position, alert.alert_id, alert.kind, alert.scope, impact, action, owner))
    return tuple(out)


def rank_actions(result, store: GovernedStore) -> tuple[RankedAction, ...]:
    return rank([(a, compute_impact(store, a, result.as_of_week)) for a in result.alerts])


class _Reader:
    """Reads one scope's windowed values through the governed store and remembers the query IDs used.

    `fact()` registers an intermediate number (exposure parts, excess_share, average price...) so every number
    behind an impact can be cited.
    """

    def __init__(self, store: GovernedStore, level: str, scope: str, as_of: int, alert_id: str):
        self.store, self.level, self.scope, self.as_of, self.ids = store, level, scope, as_of, []
        self.alert_id = alert_id

    def fact(self, name: str, value: float, unit: str, formula: str) -> float:
        if value is not None and math.isfinite(value):
            inputs = tuple(dict.fromkeys(self.ids))
            self.ids.append(self.store.register_derived(f"{self.alert_id} {self.scope} {name}", float(value), unit,
                                                        inputs, formula))
        return value

    def value(self, metric: str, window: int, scope: str | None = None, level: str | None = None) -> float | None:
        level, scope = level or self.level, scope or self.scope
        window = max(1, min(window, self.as_of + 1))
        panel = self.store.panel(metric, level, self.as_of, window)
        self.ids.append(panel.query_id)
        row = panel.values[(panel.values["scope"] == scope) & (panel.values["week"] == self.as_of)]
        value = row["value"].iloc[0] if len(row) else None
        return None if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)


def compute_impact(store: GovernedStore, alert: Alert, as_of: int) -> Impact:
    level = "portfolio" if alert.dimension == "portfolio" else alert.dimension
    read = _Reader(store, level, alert.scope, as_of, alert.alert_id)
    unsold = read.value("unsold_inventory_usd", 1)
    recent_acq = read.value("acquisition_usd", WINDOW_WEEKS)
    scope_rev = read.value("resale_usd", IMPACT_TRAILING_WEEKS)
    portfolio_rev = read.value("resale_usd", IMPACT_TRAILING_WEEKS, scope="portfolio", level="portfolio")
    signal = alert.signals[0]
    if None in (unsold, recent_acq, scope_rev) or not portfolio_rev:
        fields = sensitivity(None)  # thin data: say so instead of reporting zeros
    else:
        exposure = read.fact("exposure_usd", unsold + FORWARD_WEEKS * recent_acq / WINDOW_WEEKS, "usd",
                             f"unsold_inventory_usd + {FORWARD_WEEKS} x weekly acquisition_usd")
        share = read.fact("portfolio_share", scope_rev / portfolio_rev, "ratio",
                          "scope resale_usd / portfolio resale_usd (trailing weeks)")
        fields = _kind_fields(store, read, alert, signal.residual, exposure, share, as_of)
    return _register(store, alert, fields, tuple(dict.fromkeys(read.ids + list(signal.ref_ids))))


def _kind_fields(store, read: _Reader, alert: Alert, residual: float, exposure: float, share: float, as_of: int) -> dict:
    if alert.kind == "reno_cost_drift":
        est, rev = read.value("reno_estimate_sum", IMPACT_TRAILING_WEEKS), read.value("resale_usd", IMPACT_TRAILING_WEEKS)
        if est and rev and math.isfinite(residual):
            ratio = read.fact("reno_estimate_to_revenue", est / rev, "ratio", "reno_estimate_sum / resale_usd")
            return measured(residual * ratio * 1e4, exposure, share)
    elif alert.kind == "demand_softening":
        observed = read.value("first_offer_rate", WINDOW_WEEKS)
        dtfo = read.value("avg_days_to_first_offer", IMPACT_TRAILING_WEEKS)
        hold_bps = read.value("holding_cost_bps_per_day", IMPACT_TRAILING_WEEKS)
        if observed and dtfo and hold_bps and math.isfinite(residual):
            peer_rate = read.fact("peer_first_offer_rate", observed - residual, "ratio", "observed - peer residual")
            excess_days = read.fact("excess_days_on_market", max(0.0, dtfo * (peer_rate / observed - 1)), "days",
                                    "avg_days_to_first_offer x (peer_rate / observed_rate - 1)")
            return measured(excess_days * hold_bps, exposure, share,
                            status="lower bound (holding cost only; price-cut losses not modeled)")
    elif alert.kind == "adverse_selection":
        return _adverse_selection(store, read, alert, residual, exposure, share, as_of)
    return sensitivity(exposure)


def _adverse_selection(store, read: _Reader, alert, residual, exposure, share, as_of) -> dict:
    hold_days, resales_13 = read.value("hold_days_sum", IMPACT_TRAILING_WEEKS), read.value("resales", IMPACT_TRAILING_WEEKS)
    hold_weeks = hold_days / resales_13 / 7 if hold_days and resales_13 else float("inf")
    read.fact("avg_hold_weeks", hold_weeks, "count", "hold_days_sum / resales / 7")
    cohort_start = alert.onset_week + math.ceil(hold_weeks) if math.isfinite(hold_weeks) else as_of + 1
    cohort_resales = read.value("resales", as_of - cohort_start + 1) if cohort_start <= as_of else 0.0
    min_resales = MIN_DENOMINATOR.get("resale_vs_model_bps", DEFAULT_MIN_DENOMINATOR)
    if confirmed_by_resales(as_of - alert.onset_week, hold_weeks, cohort_resales or 0.0, min_resales):
        window = as_of - cohort_start + 1
        panel = store.panel("resale_vs_model_bps", "segment", as_of, window, min_denominator=MIN_SEGMENT_SAMPLE)
        read.ids.append(panel.query_id)
        roll = rollup(peer_residuals(panel, alert.dimension), alert.dimension)
        row = roll[(roll["scope"] == alert.scope) & (roll["week"] == as_of)]
        if len(row) and math.isfinite(row["residual"].iloc[0]):
            return measured(-float(row["residual"].iloc[0]), exposure, share, status="confirmed by resales")
    observed = read.value("contract_rate", WINDOW_WEEKS)
    closes_since = read.value("closes", as_of - alert.onset_week + 1)
    closes_recent = read.value("closes", WINDOW_WEEKS)
    acq, closes_13 = read.value("acquisition_usd", IMPACT_TRAILING_WEEKS), read.value("closes", IMPACT_TRAILING_WEEKS)
    if None in (closes_since, closes_recent) or not (observed and acq and closes_13 and math.isfinite(residual)):
        return sensitivity(exposure)
    excess_share = read.fact("excess_share", min(1.0, max(0.0, residual / observed)), "ratio",
                             "share of contracts above the peer-expected rate: residual / observed contract_rate")
    homes = read.fact("exposed_homes", exposed_homes(closes_since, cohort_resales or 0.0,
                                                    FORWARD_WEEKS * closes_recent / WINDOW_WEEKS), "count",
                      "closes since onset - post-onset cohort resales + forward weekly closes")
    avg_price = read.fact("avg_price", acq / closes_13, "usd", "acquisition_usd / closes (trailing weeks)")
    return scenario_estimate(homes, avg_price, excess_share, share)


NUMBER_UNITS = {"usd": ("usd_low", "usd_mid", "usd_high", "usd_per_100bps", "exposure_usd"),
                "bps": ("scope_bps_low", "scope_bps_mid", "scope_bps_high",
                        "portfolio_cm_bps_low", "portfolio_cm_bps_mid", "portfolio_cm_bps_high")}


def _register(store: GovernedStore, alert: Alert, fields: dict, inputs: tuple[str, ...]) -> Impact:
    ids = list(inputs)
    for unit, names in NUMBER_UNITS.items():
        for name in names:
            value = fields[name]
            if value is not None and math.isfinite(value):
                ids.append(store.register_derived(f"{alert.alert_id} {alert.kind} {alert.scope} {name}", value, unit,
                                                  inputs, f"impact:{fields['basis']}:{name}"))
    return Impact(ref_ids=tuple(ids), **{k: fields[k] for k in Impact.__dataclass_fields__ if k != "ref_ids"})
