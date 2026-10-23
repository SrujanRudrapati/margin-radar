"""Injected problems. Each scenario multiplies one or more levers inside its scope from its start week."""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np

Effect = Literal["days_to_first_offer", "conversion", "resale_vs_model", "reno_overrun"]


@dataclass(frozen=True)
class Scenario:
    name: str
    scope_type: Literal["market", "band"]
    scope: str
    start_week: int
    effects: Mapping[Effect, float]


def default_scenarios(
    a_market: str = "M02", a_start_week: int = 30,
    b_band: str = "B2", b_start_week: int = 30,
    c_market: str = "M05", c_start_week: int = 30,
) -> tuple[Scenario, ...]:
    return (
        # A: buyers slow down in one market.
        Scenario("A", "market", a_market, a_start_week, {"days_to_first_offer": 1.40}),
        # B: adverse selection — sellers accept more at the same spread because the homes are worth less.
        Scenario("B", "band", b_band, b_start_week, {"conversion": 1.25, "resale_vs_model": 0.97}),
        # C: renovation costs overrun estimates in one market.
        Scenario("C", "market", c_market, c_start_week, {"reno_overrun": 1.18}),
    )


def effect_multiplier(
    scenarios: Sequence[Scenario], effect: Effect,
    market: np.ndarray, band: np.ndarray, week: np.ndarray,
) -> np.ndarray:
    """Per-home multiplier for one lever. `week` is the week the lever acts in (NaN = never)."""
    mult = np.ones(len(week))
    for s in scenarios:
        factor = s.effects.get(effect)
        if factor is None:
            continue
        scope = market if s.scope_type == "market" else band
        hit = (scope == s.scope) & (week >= s.start_week)
        mult = np.where(hit, mult * factor, mult)
    return mult
