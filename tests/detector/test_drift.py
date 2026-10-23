import numpy as np
import pandas as pd
import pytest

from detector.config import CUSUM_H, Z_ALERT
from detector.drift import DriftScore, Insufficient, score


def series(values, start=0):
    return pd.Series(values, index=range(start, start + len(values)), dtype=float)


def test_step_change_fires():
    rng = np.random.default_rng(0)
    vals = list(rng.normal(0, 0.02, 40)) + list(0.15 + rng.normal(0, 0.02, 6))
    result = score(series(vals), as_of_week=45, metric="contract_rate")
    assert isinstance(result, DriftScore)
    assert result.fired and result.direction == "+"
    assert result.z_latest >= Z_ALERT or result.cusum_pos >= CUSUM_H


def test_negative_step_fires_minus():
    rng = np.random.default_rng(1)
    vals = list(rng.normal(0, 0.02, 40)) + list(-0.15 + rng.normal(0, 0.02, 6))
    result = score(series(vals), as_of_week=45, metric="first_offer_rate")
    assert result.fired and result.direction == "-"


def test_noise_does_not_fire():
    fired = 0
    for seed in range(200):
        vals = np.random.default_rng(seed).normal(0, 1, 60)
        result = score(series(vals), as_of_week=59, metric="contract_rate")
        fired += isinstance(result, DriftScore) and result.fired
    assert fired / 200 < 0.02


def test_short_history_insufficient():
    result = score(series(np.zeros(10)), as_of_week=9, metric="contract_rate")
    assert isinstance(result, Insufficient)
    assert "history" in result.reason


def test_missing_latest_value_insufficient():
    vals = list(np.random.default_rng(2).normal(0, 0.02, 40)) + [np.nan]
    assert isinstance(score(series(vals), as_of_week=40, metric="contract_rate"), Insufficient)


def test_onset_week_is_first_crossing():
    rng = np.random.default_rng(3)
    vals = list(rng.normal(0, 0.02, 40)) + list(0.2 + rng.normal(0, 0.01, 6))  # step starts at week 40
    result = score(series(vals), as_of_week=45, metric="contract_rate")
    assert result.onset_week == 40


def test_sampling_se_floor_damps_z():
    rng = np.random.default_rng(4)
    vals = list(rng.normal(0, 0.001, 40)) + [0.05] * 6
    loose = score(series(vals), as_of_week=45, metric="contract_rate")
    damped = score(series(vals), as_of_week=45, metric="contract_rate", se=series([0.05] * 46))
    assert abs(damped.z_latest) < abs(loose.z_latest)
    assert not damped.fired


def test_onset_stays_fixed_during_episode():
    rng = np.random.default_rng(5)
    vals = list(rng.normal(0, 0.02, 40)) + list(0.2 + rng.normal(0, 0.01, 25))
    onsets = {w: score(series(vals), as_of_week=w, metric="contract_rate").onset_week for w in (45, 50, 60)}
    assert set(onsets.values()) == {40}, onsets
    assert all(score(series(vals), as_of_week=w, metric="contract_rate").fired for w in (45, 50, 60))


def test_sustained_shift_fires_via_cusum_without_streak():
    from statsmodels.robust.scale import mad
    rng = np.random.default_rng(6)
    base = list(rng.normal(0, 1, 40))
    history = np.array(base[7:33])  # the baseline the episode freezes at week 40: last 26 weeks <= 40 - 8
    vals = base + [float(np.median(history)) + 3.0 * float(mad(history))] * 14  # z = 3.0 < Z_ALERT: CUSUM only
    result = score(series(vals), as_of_week=53, metric="contract_rate")
    assert result.fired and result.direction == "+" and result.z_streak == 0


def test_baseline_ignores_burn_in_and_is_not_frozen_by_early_noise():
    # Seed-4 failure mode: odd first weeks (burn-in) must not become a baseline that flags every later
    # normal week. Early weeks at -0.08 (burn-in), then 40 normal weeks around 0: no alert at the end.
    rng = np.random.default_rng(7)
    vals = [-0.08] * 8 + list(rng.normal(0, 0.02, 40))
    result = score(series(vals), as_of_week=47, metric="contract_rate")
    assert not result.fired
