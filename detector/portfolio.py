"""Portfolio-level abrupt-shift check for moves that hit every segment at once.

Peer residuals cancel anything common to all segments, so they cannot see a portfolio-wide shift. This
check compares the portfolio series with its own recent median: a smooth seasonal drift moves slowly,
a step change does not. Gradual all-segment shifts remain undetectable (README known limitation).
Synthetic data — not Opendoor data.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.robust.scale import mad

from detector.config import (
    EVAL_WEEKS, HISTORY_WEEKS, MIN_HISTORY_WEEKS, PORTFOLIO_BASELINE_WEEKS, PORTFOLIO_Z, SIGMA_FLOOR, WINDOW_WEEKS,
    Z_CONSECUTIVE,
)
from detector.drift import DEFAULT_SIGMA_FLOOR, Insufficient
from detector.governed import GovernedStore
from detector.models import Alert, Direction


@dataclass(frozen=True)
class PortfolioScore:
    metric: str
    z_latest: float
    z_streak: int
    direction: Direction
    fired: bool
    ref_ids: tuple[str, ...]


def portfolio_check(store: GovernedStore, metric: str, as_of_week: int) -> PortfolioScore | Insufficient:
    panel = store.panel(metric, "portfolio", as_of_week, WINDOW_WEEKS)
    values = pd.to_numeric(panel.values.set_index("week")["value"], errors="coerce")
    result = portfolio_fired(values, as_of_week, metric)
    if isinstance(result, Insufficient):
        return result
    return PortfolioScore(**{**result.__dict__, "ref_ids": (panel.query_id,)})


def portfolio_fired(values: pd.Series, as_of_week: int, metric: str) -> PortfolioScore | Insufficient:
    values = values.loc[:as_of_week].astype(float)
    jump = values - _linear_extrapolation(values)
    history = jump.loc[: as_of_week - EVAL_WEEKS].dropna().tail(HISTORY_WEEKS)
    if len(history) < MIN_HISTORY_WEEKS or pd.isna(jump.get(as_of_week, np.nan)):
        return Insufficient(f"portfolio {metric}: not enough history")
    sigma = max(float(mad(history.to_numpy())), SIGMA_FLOOR.get(metric, DEFAULT_SIGMA_FLOOR))
    z = ((jump - float(np.median(history))) / sigma).loc[as_of_week - Z_CONSECUTIVE + 1: as_of_week]
    z_latest = float(z.iloc[-1])
    sign = 1 if z_latest >= 0 else -1
    streak = int(sum(1 for _ in _takewhile_abs(z.to_numpy()[::-1], sign)))
    return PortfolioScore(metric=metric, z_latest=z_latest, z_streak=streak, direction="+" if sign > 0 else "-",
                          fired=streak >= Z_CONSECUTIVE, ref_ids=())


def _linear_extrapolation(values: pd.Series) -> pd.Series:
    """Predict each week from a straight line fitted to PORTFOLIO_BASELINE_WEEKS weeks that end
    Z_CONSECUTIVE weeks earlier, extrapolated forward.

    Seasonality is smooth, so locally it is close to a line; a step change is not. The gap keeps the
    first weeks of a step out of the line that judges them.
    """
    n, gap = PORTFOLIO_BASELINE_WEEKS, Z_CONSECUTIVE
    x = np.arange(n, dtype=float)
    predicted = {}
    for week in values.index:
        prior = values.loc[week - gap - n + 1: week - gap]
        if len(prior) == n and prior.notna().all():
            slope, intercept = np.polyfit(x, prior.to_numpy(), 1)
            predicted[week] = intercept + slope * (n - 1 + gap)
    return pd.Series(predicted, dtype=float).reindex(values.index)


def _takewhile_abs(values, sign):
    for value in values:
        if np.isnan(value) or value * sign < PORTFOLIO_Z:
            return
        yield value


def suppress_explained(scores: list[PortfolioScore], alerts: list[Alert]) -> list[PortfolioScore]:
    explained = {(s.metric, s.direction) for a in alerts for s in a.signals}
    return [p for p in scores if p.fired and (p.metric, p.direction) not in explained]
