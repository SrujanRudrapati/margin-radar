"""Answer key for evaluation. Never loaded into DuckDB.

For each scenario, the week its problem first shows up in sold-cohort contribution margin
is measured from data: run the scenario alone and the control with the same seed (shared
draws), and find the first resale week where the scope's CM is at least CM_VISIBLE_BPS
below control for CM_VISIBLE_CONSECUTIVE weeks in a row.
"""
from collections.abc import Sequence
from datetime import timedelta

import numpy as np
import pandas as pd

from generator.config import N_WEEKS, SEGMENTS, START_DATE
from generator.metrics import sold_cohort_cm
from generator.scenarios import Scenario
from generator.simulate import simulate

CM_VISIBLE_BPS = 50
CM_VISIBLE_CONSECUTIVE = 2


def compute_ground_truth(seed: int, scenarios: Sequence[Scenario]) -> list[dict]:
    control = simulate(seed).homes
    return [_truth_for(s, simulate(seed, (s,)).homes, control) for s in scenarios]


def _truth_for(s: Scenario, solo: pd.DataFrame, control: pd.DataFrame) -> dict:
    visible = _first_visible_week(s, solo, control)
    return {
        "scenario": s.name,
        "effects": dict(s.effects),
        "scope_type": s.scope_type,
        "scope": s.scope,
        "segments": [seg for seg in SEGMENTS if _segment_in_scope(seg, s)],
        "start_week": s.start_week,
        "start_date": _week_date(s.start_week),
        "cm_first_visible_week": visible,
        "cm_first_visible_date": None if visible is None else _week_date(visible),
        "cm_lag_weeks": None if visible is None else visible - s.start_week,
    }


def _first_visible_week(s: Scenario, solo: pd.DataFrame, control: pd.DataFrame) -> int | None:
    weeks = pd.RangeIndex(N_WEEKS, name="resale_week")
    cm = {
        name: sold_cohort_cm(h[h[s.scope_type] == s.scope]).set_index("resale_week")["cm_pct"].reindex(weeks)
        for name, h in (("solo", solo), ("control", control))
    }
    below = ((cm["solo"] - cm["control"]) * 1e4 <= -CM_VISIBLE_BPS).to_numpy()
    for w in range(s.start_week, N_WEEKS - CM_VISIBLE_CONSECUTIVE + 1):
        if np.all(below[w:w + CM_VISIBLE_CONSECUTIVE]):
            return w
    return None


def _segment_in_scope(segment: str, s: Scenario) -> bool:
    market, band, _ = segment.split("-")
    return (market if s.scope_type == "market" else band) == s.scope


def _week_date(week: int) -> str:
    return (START_DATE + timedelta(weeks=week)).isoformat()
