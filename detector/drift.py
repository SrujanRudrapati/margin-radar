"""Robust z-score and two-sided CUSUM of a residual series against its own trailing history.

Synthetic data — not Opendoor data. Scores are uncalibrated: they rank how unusual a move is, they
are not probabilities that an alert is real.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.robust.scale import mad

from detector.config import (
    BURN_IN_WEEKS, CUSUM_H, CUSUM_K, CUSUM_SCALE, EVAL_WEEKS, MIN_HISTORY_WEEKS, SIGMA_FLOOR, Z_ALERT, Z_CONSECUTIVE,
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
    """Replay the series up to as_of_week (no look-ahead) as episodes.

    Each week is scored against an expanding baseline: the median and robust scale of every valid residual after
    the burn-in and at least EVAL_WEEKS earlier. A long baseline is robust to a drift until the drift dominates
    it, so a persistent drift keeps scoring high without freezing anything, and early noise cannot lock in
    (DECISIONS D16). A CUSUM run (in either direction) is an episode with a fixed onset (stable alert IDs). An
    episode fires on a z-streak (|z| >= Z_ALERT for Z_CONSECUTIVE weeks) or when its CUSUM reaches CUSUM_H, and
    stays fired until its CUSUM returns to zero.
    """
    residual = residual.loc[:as_of_week]
    if pd.isna(residual.get(as_of_week, np.nan)):
        return Insufficient(f"no usable value in week {as_of_week} (thin data)")
    state = _Episode()
    for week in residual.index:
        base = _baseline(residual, week, metric)
        if base is None:
            continue
        sigma = base[1]
        if se is not None and pd.notna(se.get(week, np.nan)):
            sigma = max(sigma, float(se.get(week)))
        value = residual.loc[week]
        state.step(week, 0.0 if pd.isna(value) else (value - base[0]) / sigma, base)
    if state.weeks_scored == 0:
        return Insufficient(f"fewer than {MIN_HISTORY_WEEKS} weeks of history")
    return state.result(as_of_week)


def _baseline(residual: pd.Series, week: int, metric: str) -> tuple[float, float] | None:
    history = residual.loc[BURN_IN_WEEKS: week - EVAL_WEEKS].dropna()
    if len(history) < MIN_HISTORY_WEEKS:
        return None
    sigma = max(float(mad(history.to_numpy())), SIGMA_FLOOR.get(metric, DEFAULT_SIGMA_FLOOR))
    return float(np.median(history)), sigma


class _Episode:
    """Two-sided CUSUM with a z-streak rule; tracks the current run (episode) in each direction."""

    def __init__(self):
        self.pos = self.neg = 0.0
        self.pos_start = self.neg_start = None
        self.pos_fired = self.neg_fired = False
        self.streak, self.streak_sign, self.z, self.weeks_scored = 0, 0, 0.0, 0
        self.baseline = (0.0, 0.0)

    def step(self, week: int, z: float, base: tuple[float, float]) -> None:
        self.weeks_scored += 1
        self.z, self.baseline = z, base
        pos = max(0.0, self.pos + z / CUSUM_SCALE - CUSUM_K)
        neg = max(0.0, self.neg - z / CUSUM_SCALE - CUSUM_K)
        if self.pos == 0 and pos > 0:
            self.pos_start = week
        if self.neg == 0 and neg > 0:
            self.neg_start = week
        if pos == 0:
            self.pos_start, self.pos_fired = None, False
        if neg == 0:
            self.neg_start, self.neg_fired = None, False
        sign = 1 if z >= Z_ALERT else (-1 if z <= -Z_ALERT else 0)
        self.streak = self.streak + 1 if sign != 0 and sign == self.streak_sign else (1 if sign else 0)
        self.streak_sign = sign
        if self.streak >= Z_CONSECUTIVE:
            self.pos_fired |= sign > 0 and pos > 0
            self.neg_fired |= sign < 0 and neg > 0
        self.pos_fired |= pos >= CUSUM_H
        self.neg_fired |= neg >= CUSUM_H
        self.pos, self.neg = pos, neg

    def result(self, as_of_week: int) -> DriftScore:
        if self.pos_fired and (not self.neg_fired or self.pos >= self.neg):
            direction, start, fired = "+", self.pos_start, True
        elif self.neg_fired:
            direction, start, fired = "-", self.neg_start, True
        else:
            direction = "+" if self.pos >= self.neg else "-"
            start, fired = (self.pos_start if direction == "+" else self.neg_start), False
        onset = int(start) if start is not None else as_of_week
        streak = self.streak if (self.streak_sign > 0) == (direction == "+") else 0
        return DriftScore(z_latest=float(self.z), z_streak=streak, cusum_pos=self.pos, cusum_neg=self.neg,
                          direction=direction, onset_week=onset, fired=fired, baseline=self.baseline[0],
                          sigma=self.baseline[1])
