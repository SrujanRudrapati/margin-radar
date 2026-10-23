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
    frame["peer_median"], frame["n_peers"] = _leave_one_out(frame, dimension, groups)
    ok = frame["value"].notna() & (frame["n_peers"] >= MIN_PEERS[dimension])
    frame["residual"] = np.where(ok, frame["value"] - frame["peer_median"], np.nan)
    frame["weight"] = np.where(ok, pd.to_numeric(frame["denominator"], errors="coerce").fillna(0), 0.0)
    frame["metric"] = panel.metric
    return frame.drop(columns="denominator").reset_index(drop=True)


def _leave_one_out(frame: pd.DataFrame, dimension: str, groups: list[str]) -> tuple[pd.Series, pd.Series]:
    """Median and count of the other segments in the same group (same week and other two dimensions)."""
    wide = frame.pivot_table(index=groups, columns=dimension, values="value", aggfunc="first", dropna=False)
    matrix = wide.to_numpy(dtype=float)
    medians = np.full_like(matrix, np.nan)
    counts = np.zeros_like(matrix)
    for j in range(matrix.shape[1]):
        others = np.delete(matrix, j, axis=1)
        counts[:, j] = np.sum(~np.isnan(others), axis=1)
        has_peers = counts[:, j] > 0
        medians[has_peers, j] = np.nanmedian(others[has_peers], axis=1)
    long = pd.DataFrame({
        "median": pd.DataFrame(medians, index=wide.index, columns=wide.columns).stack(future_stack=True),
        "count": pd.DataFrame(counts, index=wide.index, columns=wide.columns).stack(future_stack=True),
    })
    keyed = frame.set_index(groups + [dimension]).index
    joined = long.reindex(keyed)
    return (pd.Series(joined["median"].to_numpy(), index=frame.index),
            pd.Series(joined["count"].fillna(0).astype(int).to_numpy(), index=frame.index))


def rollup(residuals: pd.DataFrame, dimension: Dimension) -> pd.DataFrame:
    metric = residuals["metric"].iloc[0] if len(residuals) else ""
    min_weight = MIN_DENOMINATOR.get(metric, DEFAULT_MIN_DENOMINATOR)
    frame = residuals.assign(
        weighted=residuals["residual"].fillna(0) * residuals["weight"],
        weighted_peer=residuals["peer_median"].fillna(0) * residuals["weight"],
        valid=residuals["residual"].notna(),
    )
    frame["weighted_sq"] = frame["residual"].fillna(0) ** 2 * frame["weight"]
    out = (
        frame.groupby([dimension, "week"])
        .agg(weighted=("weighted", "sum"), weighted_peer=("weighted_peer", "sum"), weighted_sq=("weighted_sq", "sum"),
             weight=("weight", "sum"), n_segments=("valid", "sum"))
        .reset_index()
        .rename(columns={dimension: "scope"})
    )
    usable = (out["n_segments"] >= 2) & (out["weight"] >= min_weight) & (out["weight"] > 0)
    out["residual"] = np.where(usable, out["weighted"] / out["weight"].where(out["weight"] > 0), np.nan)
    # Volume-weighted peer rate: the level the scope is compared against (used for sampling error).
    out["peer_level"] = np.where(usable, out["weighted_peer"] / out["weight"].where(out["weight"] > 0), np.nan)
    # Standard error of the pooled residual from how much the scope's own segments disagree that week
    # (weighted sd / sqrt(n)); a data-derived noise floor for the drift score (DECISIONS D9).
    mean_sq = out["weighted_sq"] / out["weight"].where(out["weight"] > 0)
    spread = np.sqrt((mean_sq - out["residual"] ** 2).clip(lower=0))
    out["se"] = np.where(usable, spread / np.sqrt(out["n_segments"].clip(lower=1)), np.nan)
    return out[["scope", "week", "residual", "weight", "n_segments", "peer_level", "se"]]
