"""detect(): peer residuals → rollups → drift scores → classification rules. Synthetic data — not Opendoor data.

Margin itself (contribution_margin_pct, resale_vs_model_bps) never triggers: it is the lagging outcome the
leading indicators are meant to front-run.
"""
import hashlib
import math

import numpy as np
import pandas as pd

from detector.config import MIN_SEGMENT_SAMPLE, WINDOW_WEEKS, Z_EXPLAIN
from detector.drift import DriftScore, Insufficient, score
from detector.governed import GovernedStore
from detector.models import Abstention, Alert, DetectorResult, Signal, Watch
from detector.peers import peer_residuals, rollup
from detector.portfolio import PortfolioScore, portfolio_check, suppress_explained

DIMENSIONS = ("market", "band")
# trigger metric -> (direction that hurts margin, alert kind)
TRIGGERS = {
    "contract_rate": ("+", "adverse_selection"),
    "first_offer_rate": ("-", "demand_softening"),
    "reno_overrun_pct": ("+", "reno_cost_drift"),
}
SUPPORTING = {"demand_softening": (("price_cut_rate", "+"), ("showing_rate_per_week", "-"))}
EXPLAINING_METRIC = "avg_spread_pct"
PROPORTION_METRICS = frozenset({"contract_rate", "first_offer_rate", "price_cut_rate"})

Scored = dict[str, tuple[DriftScore | Insufficient, pd.DataFrame, str]]


def detect(store: GovernedStore, as_of_week: int) -> DetectorResult:
    scored = {(m, d): _score_metric(store, m, d, as_of_week)
              for m in _metrics_needed() for d in DIMENSIONS}
    alerts: list[Alert] = []
    watch: list[Watch] = []
    for metric, (bad, kind) in TRIGGERS.items():
        for dim in DIMENSIONS:
            for scope, (result, roll, panel_id) in scored[(metric, dim)].items():
                if not (isinstance(result, DriftScore) and result.fired):
                    continue
                signal = _signal(store, metric, dim, scope, result, roll, panel_id, as_of_week)
                if result.direction != bad:
                    watch.append(Watch(scope, metric, f"{metric} moved {result.direction} (not the margin-risk "
                                                      f"direction); uncalibrated score {result.z_latest:.1f}",
                                       signal.ref_ids))
                    continue
                if kind == "adverse_selection":
                    spread = scored[(EXPLAINING_METRIC, dim)].get(scope, (None,))[0]
                    verdict, note = classify_adverse_selection(result, spread if isinstance(spread, DriftScore) else None)
                    if verdict == "watch":
                        watch.append(Watch(scope, metric, note, signal.ref_ids))
                        continue
                supporting = _supporting(store, scored, kind, dim, scope, as_of_week)
                alerts.append(_alert(store.run_id, kind, dim, scope, signal, supporting))
    alerts += _portfolio_alerts(store, as_of_week, alerts)
    abstentions = _abstentions(scored)
    if not alerts and _all_insufficient(scored):
        abstentions = [Abstention("all", None, "no trigger metric has enough history or volume yet")] + abstentions
    return DetectorResult(store.run_id, as_of_week, tuple(sorted(alerts, key=lambda a: (a.kind, a.scope))),
                          tuple(watch), tuple(abstentions))


def classify_adverse_selection(conversion: DriftScore, spread: DriftScore | None) -> tuple[str, str]:
    """Conversion up at unchanged spread is adverse selection; up because offers got richer is not."""
    if spread is not None and spread.direction == "-" and abs(spread.z_latest) >= Z_EXPLAIN:
        return "watch", "conversion rose but spread fell (richer offers) — explained by spread, not adverse selection"
    return "alert", "conversion rose with no matching spread change"


def _metrics_needed() -> tuple[str, ...]:
    extra = [EXPLAINING_METRIC] + [m for pairs in SUPPORTING.values() for m, _ in pairs]
    return tuple(TRIGGERS) + tuple(extra)


def _score_metric(store: GovernedStore, metric: str, dim: str, as_of_week: int) -> Scored:
    panel = store.panel(metric, "segment", as_of_week, WINDOW_WEEKS, min_denominator=MIN_SEGMENT_SAMPLE)
    roll = rollup(peer_residuals(panel, dim), dim)
    out: Scored = {}
    for scope, frame in roll.groupby("scope"):
        indexed = frame.set_index("week")
        series = indexed["residual"]
        se = indexed["se"].fillna(0.0)
        if metric in PROPORTION_METRICS:
            p, n = indexed["peer_level"], indexed["weight"]
            se = np.maximum(se, np.sqrt((p * (1 - p)).clip(lower=1e-4) / n.where(n > 0)).fillna(0.0))
        out[scope] = (score(series, as_of_week, metric, se), frame, panel.query_id)
    return out


def _signal(store, metric, dim, scope, result: DriftScore, roll, panel_id, as_of_week) -> Signal:
    residual = float(roll.set_index("week")["residual"].loc[as_of_week])
    ids = [panel_id]
    if math.isfinite(residual):
        ids.append(store.register_derived(f"{metric} {dim} peer residual {scope} week {as_of_week}", residual,
                                          "ratio", (panel_id,), "volume-weighted mean of leave-one-out peer residuals"))
    ids.append(store.register_derived(f"{metric} {dim} drift score {scope} week {as_of_week}", result.z_latest,
                                      "ratio", (panel_id,), "robust z vs trailing history (uncalibrated)"))
    return Signal(metric, dim, scope, result.direction, result.z_latest, residual, result.onset_week, tuple(ids))


def _supporting(store, scored, kind, dim, scope, as_of_week) -> tuple[Signal, ...]:
    out = []
    for metric, direction in SUPPORTING.get(kind, ()):
        result, roll, panel_id = scored[(metric, dim)].get(scope, (None, None, None))
        if isinstance(result, DriftScore) and result.fired and result.direction == direction:
            out.append(_signal(store, metric, dim, scope, result, roll, panel_id, as_of_week))
    return tuple(out)


def _alert(run_id, kind, dim, scope, signal: Signal, supporting) -> Alert:
    key = f"{run_id}|{kind}|{scope}|{signal.onset_week}"
    return Alert("A" + hashlib.sha256(key.encode()).hexdigest()[:8], kind, dim, scope, signal.onset_week,
                 (signal,), supporting)


def _portfolio_alerts(store: GovernedStore, as_of_week: int, alerts: list[Alert]) -> list[Alert]:
    scores = [s for s in (portfolio_check(store, m, as_of_week) for m in TRIGGERS) if isinstance(s, PortfolioScore)]
    out = []
    for p in suppress_explained(scores, alerts):
        onset = as_of_week - p.z_streak + 1
        ids = p.ref_ids + (store.register_derived(f"{p.metric} portfolio shift score week {as_of_week}", p.z_latest,
                                                  "ratio", p.ref_ids, "abrupt-shift robust z (uncalibrated)"),)
        signal = Signal(p.metric, "portfolio", "portfolio", p.direction, p.z_latest, float("nan"), onset, ids)
        out.append(_alert(store.run_id, "portfolio_shift", "portfolio", "portfolio", signal, ()))
    return out


def _abstentions(scored) -> list[Abstention]:
    return [Abstention(scope, metric, result.reason)
            for (metric, _), scopes in scored.items() if metric in TRIGGERS
            for scope, (result, _, _) in scopes.items() if isinstance(result, Insufficient)]


def _all_insufficient(scored) -> bool:
    return all(isinstance(result, Insufficient)
               for (metric, _), scopes in scored.items() if metric in TRIGGERS
               for result, _, _ in scopes.values())
