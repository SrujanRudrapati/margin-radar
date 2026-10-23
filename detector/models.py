"""Detector result types. Synthetic data — not Opendoor data."""
from dataclasses import dataclass
from typing import Literal

Direction = Literal["+", "-"]
Kind = Literal["adverse_selection", "demand_softening", "reno_cost_drift", "portfolio_shift"]


@dataclass(frozen=True)
class Signal:
    metric: str
    dimension: str
    scope: str
    direction: Direction
    z: float  # uncalibrated score, not a probability
    residual: float
    onset_week: int
    ref_ids: tuple[str, ...]  # panel query_ids + derived residual/score ids


@dataclass(frozen=True)
class Alert:
    alert_id: str  # "A" + sha256(run_id|kind|scope|onset_week)[:8]
    kind: Kind
    dimension: Literal["market", "band", "portfolio"]
    scope: str
    onset_week: int
    signals: tuple[Signal, ...]
    supporting: tuple[Signal, ...]


@dataclass(frozen=True)
class Watch:
    scope: str
    metric: str
    note: str
    ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class Abstention:
    scope: str
    metric: str | None
    reason: str


@dataclass(frozen=True)
class DetectorResult:
    run_id: str
    as_of_week: int
    alerts: tuple[Alert, ...]
    watch: tuple[Watch, ...]
    abstentions: tuple[Abstention, ...]
