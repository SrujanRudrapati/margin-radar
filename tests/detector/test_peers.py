import math

import numpy as np
import pandas as pd
import pytest

from detector.governed import MetricPanel
from detector.peers import peer_residuals, rollup

MARKETS = ["M01", "M02", "M03", "M04", "M05", "M06"]
BANDS = ["B1", "B2", "B3"]
PRODUCTS = ["cash", "CNML"]


def make_panel(value_fn, weeks=range(3, 13), denom=100, metric="contract_rate"):
    rows = [
        {"scope": f"{m}-{b}-{p}", "market": m, "band": b, "product": p, "week": w,
         "value": value_fn(m, b, p, w), "denominator": denom}
        for m in MARKETS for b in BANDS for p in PRODUCTS for w in weeks
    ]
    return MetricPanel(query_id="Qtest", metric=metric, run_id="test", level="segment", as_of_week=max(weeks),
                       window_weeks=4, values=pd.DataFrame(rows), sql="-- test")


def base(m, b, p, w):
    # Distinct, deterministic levels per segment so medians are non-trivial.
    return 0.30 + 0.01 * MARKETS.index(m) + 0.02 * BANDS.index(b) + 0.005 * PRODUCTS.index(p)


def _row(frame, segment, week):
    return frame[(frame["segment"] == segment) & (frame["week"] == week)].iloc[0]


def test_peers_exclude_dimension_under_test():
    panel = make_panel(base)
    band = peer_residuals(panel, "band")
    r = _row(band, "M01-B1-cash", 5)
    assert r["n_peers"] == 2
    assert r["peer_median"] == pytest.approx(np.median([base("M01", "B2", "cash", 5), base("M01", "B3", "cash", 5)]))
    market = peer_residuals(panel, "market")
    r = _row(market, "M01-B1-cash", 5)
    assert r["n_peers"] == 5
    assert r["peer_median"] == pytest.approx(np.median([base(m, "B1", "cash", 5) for m in MARKETS[1:]]))


def test_leave_one_out():
    # M01 is an outlier at 0.90; including it would pull the median of the 6 markets up.
    panel = make_panel(lambda m, b, p, w: 0.90 if m == "M01" else base(m, b, p, w))
    r = _row(peer_residuals(panel, "market"), "M01-B2-CNML", 7)
    expected = np.median([base(m, "B2", "CNML", 7) for m in MARKETS[1:]])
    assert r["peer_median"] == pytest.approx(expected)
    assert r["residual"] == pytest.approx(0.90 - expected)


def test_common_shift_cancels():
    plain = peer_residuals(make_panel(base), "market")
    shifted = peer_residuals(make_panel(lambda m, b, p, w: base(m, b, p, w) + (0.10 if w == 10 else 0)), "market")
    pd.testing.assert_series_equal(plain["residual"], shifted["residual"], check_exact=False, atol=1e-12)


def test_market_shift_shows_in_rollup():
    panel = make_panel(lambda m, b, p, w: base(m, b, p, w) + (0.10 if m == "M02" else 0))
    roll = rollup(peer_residuals(panel, "market"), "market")
    plain = rollup(peer_residuals(make_panel(base), "market"), "market")
    delta = roll.set_index(["scope", "week"])["residual"] - plain.set_index(["scope", "week"])["residual"]
    assert delta.xs("M02", level="scope").to_numpy() == pytest.approx(0.10, abs=1e-9)
    others = delta.drop("M02", level="scope")
    assert others.abs().max() < 0.02
    assert set(roll.columns) >= {"scope", "week", "residual", "weight", "n_segments", "peer_level"}
    m01 = roll.set_index(["scope", "week"]).loc[("M01", 5)]
    assert 0.25 < m01["peer_level"] < 0.40


def test_thin_segment_excluded():
    panel = make_panel(lambda m, b, p, w: None if (m, b, p) == ("M03", "B2", "cash") else base(m, b, p, w))
    res = peer_residuals(panel, "market")
    thin = res[res["segment"] == "M03-B2-cash"]
    assert thin["residual"].isna().all()
    assert (thin["weight"] == 0).all()
    roll = rollup(res, "market").set_index(["scope", "week"])
    m03 = roll.loc[("M03", 5)]
    assert m03["n_segments"] == 5  # 6 segments in M03, one thin
    assert math.isfinite(m03["residual"])


def test_too_few_peers_is_nan():
    # Only M01 and M02 have values for band B1 / cash: each has 1 market peer < MIN_PEERS["market"] (3).
    panel = make_panel(lambda m, b, p, w: base(m, b, p, w) if (b, p) != ("B1", "cash") or m in ("M01", "M02") else None)
    res = peer_residuals(panel, "market")
    r = _row(res, "M01-B1-cash", 6)
    assert r["n_peers"] == 1
    assert math.isnan(r["residual"]) and r["weight"] == 0


def test_rollup_needs_two_segments_and_min_weight():
    panel = make_panel(base, denom=3)  # 6 segments x 3 = 18 < MIN_DENOMINATOR["contract_rate"] (30)
    roll = rollup(peer_residuals(panel, "market"), "market")
    assert roll["residual"].isna().all()


def test_shrinkage_pulls_thin_residuals_toward_peers():
    panel = make_panel(lambda m, b, p, w: 0.90 if m == "M01" else base(m, b, p, w), denom=100)
    plain = _row(peer_residuals(panel, "market", shrink_k=0), "M01-B2-CNML", 7)["residual"]
    shrunk = _row(peer_residuals(panel, "market", shrink_k=100), "M01-B2-CNML", 7)["residual"]
    assert shrunk == pytest.approx(plain * 100 / (100 + 100))


def test_no_shrinkage_by_default():
    panel = make_panel(lambda m, b, p, w: 0.90 if m == "M01" else base(m, b, p, w), denom=100)
    r = _row(peer_residuals(panel, "market"), "M01-B2-CNML", 7)["residual"]
    assert r == pytest.approx(0.90 - np.median([base(m, "B2", "CNML", 7) for m in MARKETS[1:]]))
