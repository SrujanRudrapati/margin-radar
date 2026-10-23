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
