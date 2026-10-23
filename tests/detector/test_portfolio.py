import numpy as np
import pandas as pd

from detector.portfolio import PortfolioScore, portfolio_fired, suppress_explained
from detector.models import Alert, Signal


def series(values):
    return pd.Series(values, index=range(len(values)), dtype=float)


def test_step_fires():
    rng = np.random.default_rng(0)
    vals = 0.35 * (1 + rng.normal(0, 0.01, 60))
    vals[50:] *= 1.30
    # Step at week 50: the first week with a 2-week streak (weeks 50, 51) is 51.
    result = portfolio_fired(series(vals), as_of_week=51, metric="contract_rate")
    assert isinstance(result, PortfolioScore)
    assert result.fired and result.direction == "+"
    assert not portfolio_fired(series(vals), as_of_week=49, metric="contract_rate").fired


def test_smooth_seasonal_does_not_fire():
    rng = np.random.default_rng(1)
    weeks = np.arange(78)
    vals = 0.35 * (1 + 0.20 * np.sin(2 * np.pi * weeks / 52)) * (1 + rng.normal(0, 0.01, 78))
    for as_of in range(30, 78):
        result = portfolio_fired(series(vals), as_of_week=as_of, metric="contract_rate")
        assert not (isinstance(result, PortfolioScore) and result.fired), as_of


def _signal(metric, direction, scope="B2", dim="band"):
    return Signal(metric=metric, dimension=dim, scope=scope, direction=direction, z=4.0, residual=0.1,
                  onset_week=40, ref_ids=("Qx",))


def test_suppressed_when_explained_by_dimension_alert():
    alert = Alert(alert_id="Aabc", kind="adverse_selection", dimension="band", scope="B2", onset_week=40,
                  signals=(_signal("contract_rate", "+"),), supporting=())
    same = PortfolioScore(metric="contract_rate", z_latest=5.0, z_streak=2, direction="+", fired=True, ref_ids=("Qp",))
    other = PortfolioScore(metric="reno_overrun_pct", z_latest=5.0, z_streak=2, direction="+", fired=True, ref_ids=("Qp",))
    assert suppress_explained([same, other], [alert]) == [other]
