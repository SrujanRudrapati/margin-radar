"""Leave-one-out peer residuals and volume-weighted rollups.

A segment is compared with segments that share the other two dimensions in the same week, so anything
common to all of them (seasonality) cancels. Synthetic data — not Opendoor data.
"""
from typing import Literal

import numpy as np
import pandas as pd

from detector.config import MIN_PEERS
from detector.governed import DEFAULT_MIN_DENOMINATOR, MIN_DENOMINATOR, MetricPanel

Dimension = Literal["market", "band"]
_DIMS = ("market", "band", "product")


def peer_residuals(panel: MetricPanel, dimension: Dimension) -> pd.DataFrame:
    if panel.level != "segment":
        raise ValueError("peer_residuals needs a segment-level panel")
    if dimension not in MIN_PEERS:
        raise ValueError(f"unknown dimension {dimension!r}")
    frame = panel.values.rename(columns={"scope": "segment"})
    frame = frame[["segment", *_DIMS, "week", "value", "denominator"]].copy()
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    groups = [d for d in _DIMS if d != dimension] + ["week"]
    frame["peer_median"], frame["n_peers"] = _leave_one_out(frame, groups)
    ok = frame["value"].notna() & (frame["n_peers"] >= MIN_PEERS[dimension])
    frame["residual"] = np.where(ok, frame["value"] - frame["peer_median"], np.nan)
    frame["weight"] = np.where(ok, pd.to_numeric(frame["denominator"], errors="coerce").fillna(0), 0.0)
    frame["metric"] = panel.metric
    return frame.drop(columns="denominator").reset_index(drop=True)


def _leave_one_out(frame: pd.DataFrame, groups: list[str]) -> tuple[pd.Series, pd.Series]:
    medians = pd.Series(np.nan, index=frame.index)
    counts = pd.Series(0, index=frame.index)
    for _, idx in frame.groupby(groups).groups.items():
        values = frame.loc[idx, "value"].to_numpy(dtype=float)
        for pos, row in enumerate(idx):
            others = np.delete(values, pos)
            others = others[~np.isnan(others)]
            counts[row] = len(others)
            medians[row] = np.median(others) if len(others) else np.nan
    return medians, counts


def rollup(residuals: pd.DataFrame, dimension: Dimension) -> pd.DataFrame:
    metric = residuals["metric"].iloc[0] if len(residuals) else ""
    min_weight = MIN_DENOMINATOR.get(metric, DEFAULT_MIN_DENOMINATOR)
    frame = residuals.assign(
        weighted=residuals["residual"].fillna(0) * residuals["weight"],
        valid=residuals["residual"].notna(),
    )
    out = (
        frame.groupby([dimension, "week"])
        .agg(weighted=("weighted", "sum"), weight=("weight", "sum"), n_segments=("valid", "sum"))
        .reset_index()
        .rename(columns={dimension: "scope"})
    )
    usable = (out["n_segments"] >= 2) & (out["weight"] >= min_weight) & (out["weight"] > 0)
    out["residual"] = np.where(usable, out["weighted"] / out["weight"].where(out["weight"] > 0), np.nan)
    return out[["scope", "week", "residual", "weight", "n_segments"]]
