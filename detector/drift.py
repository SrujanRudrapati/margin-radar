"""Robust z-score and two-sided CUSUM of a residual series against its own trailing history.

Synthetic data — not Opendoor data. Scores are uncalibrated: they rank how unusual a move is, they
are not probabilities that an alert is real.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.robust.scale import mad

from detector.config import (
    CUSUM_H, CUSUM_K, CUSUM_SCALE, EVAL_WEEKS, HISTORY_WEEKS, MIN_HISTORY_WEEKS, SIGMA_FLOOR, Z_ALERT, Z_CONSECUTIVE,
)
from detector.models import Direction

DEFAULT_SIGMA_FLOOR = 1e-6


@dataclass(frozen=True)
class DriftScore:
    z_latest: float
    z_streak: int
    cusum_pos: float
    cusum_neg: float
    direction: Direction
    onset_week: int
    fired: bool
    baseline: float
    sigma: float


@dataclass(frozen=True)
class Insufficient:
    reason: str


def score(residual: pd.Series, as_of_week: int, metric: str, se: pd.Series | None = None) -> DriftScore | Insufficient:
    residual = residual.loc[:as_of_week]
    if pd.isna(residual.get(as_of_week, np.nan)):
        return Insufficient(f"no usable value in week {as_of_week} (thin data)")
    eval_start = as_of_week - EVAL_WEEKS + 1
    history = residual.loc[: eval_start - 1].dropna().tail(HISTORY_WEEKS)
    if len(history) < MIN_HISTORY_WEEKS:
        return Insufficient(f"only {len(history)} weeks of history (need {MIN_HISTORY_WEEKS})")
    baseline = float(np.median(history))
    hist_sigma = max(float(mad(history.to_numpy())), SIGMA_FLOOR.get(metric, DEFAULT_SIGMA_FLOOR))
    window = residual.loc[eval_start:as_of_week]
    sigmas = pd.Series(hist_sigma, index=window.index)
    if se is not None:
        sigmas = np.maximum(sigmas, se.reindex(window.index).fillna(0.0))
    z = ((window - baseline) / sigmas).fillna(0.0)
    return _summarize(z, baseline, hist_sigma, as_of_week)


def _summarize(z: pd.Series, baseline: float, sigma: float, as_of_week: int) -> DriftScore:
    pos, neg = 0.0, 0.0
    pos_start, neg_start = None, None
    for week, value in z.items():
        pos_start = week if pos == 0 else pos_start
        neg_start = week if neg == 0 else neg_start
        pos = max(0.0, pos + value / CUSUM_SCALE - CUSUM_K)
        neg = max(0.0, neg - value / CUSUM_SCALE - CUSUM_K)
        pos_start = None if pos == 0 else pos_start
        neg_start = None if neg == 0 else neg_start
    z_latest = float(z.loc[as_of_week])
    sign = 1 if z_latest >= 0 else -1
    streak = 0
    for value in reversed(z.to_numpy()):
        if value * sign >= Z_ALERT:
            streak += 1
        else:
            break
    fired_streak = streak >= Z_CONSECUTIVE
    fired_cusum = max(pos, neg) >= CUSUM_H
    if fired_streak:
        direction = "+" if sign > 0 else "-"
    else:
        direction = "+" if pos >= neg else "-"
    start = pos_start if direction == "+" else neg_start
    onset = int(start) if start is not None else as_of_week - streak + 1
    return DriftScore(z_latest=z_latest, z_streak=streak, cusum_pos=pos, cusum_neg=neg, direction=direction,
                      onset_week=onset, fired=fired_streak or fired_cusum, baseline=baseline, sigma=sigma)
