"""Citable facts for the brief: deterministic display strings and their parsing. Synthetic data — not Opendoor data.

Every number a tool hands the model is registered as a derived fact in the governed store and shipped as
{"value": "<display>", "ref": "q:<fact id>"}. The model copies the display string and the reference; it never
computes. The grounding checker parses numbers back with `parse_number` and compares them with the fact.
"""
import math
import re
from dataclasses import dataclass

from detector.governed import GovernedStore

# display kind -> store unit
STORE_UNIT = {"usd": "usd", "pct": "pct", "pct_points": "pct", "bps": "bps", "count": "count", "days": "days",
              "score": "ratio", "ratio": "ratio"}

METRIC_KIND = {
    "contract_rate": "pct", "first_offer_rate": "pct", "price_cut_rate": "pct", "fall_through_rate": "pct",
    "company_decline_rate": "pct", "avg_spread_pct": "pct", "reno_overrun_pct": "pct",
    "contribution_margin_pct": "pct", "resale_vs_model_bps": "bps", "holding_cost_bps_per_day": "bps",
    "avg_days_to_first_offer": "days", "showing_rate_per_week": "ratio", "offers": "count", "closes": "count",
    "acquisition_usd": "usd", "resale_usd": "usd", "unsold_inventory_usd": "usd",
}


def residual_kind(metric_kind: str) -> str:
    return "pct_points" if metric_kind == "pct" else metric_kind


def fmt(value: float, kind: str) -> str:
    decimals = {"pct": 3, "pct_points": 3, "bps": 0, "count": 0, "days": 1, "score": 1}.get(kind)
    if decimals is not None and round(value, decimals) == 0:
        value = 0.0  # never display a negative zero
    if kind == "usd":
        sign, v = ("-" if value < 0 else ""), abs(value)
        if v >= 1e6:
            return f"{sign}${v / 1e6:.1f}M"
        if v >= 1e3:
            return f"{sign}${v / 1e3:.0f}K"
        return f"{sign}${v:,.0f}"
    if kind == "pct":
        return f"{value * 100:.1f}%"
    if kind == "pct_points":
        return f"{value * 100:+.1f} pts"
    if kind == "bps":
        return f"{value:,.0f} bps"
    if kind == "count":
        return f"{value:,.0f}"
    if kind == "days":
        return f"{value:.1f} days"
    if kind == "score":
        return f"{value:.1f}"
    return f"{value:.2f}"


_NUMBER = re.compile(r"(?P<sign>[+-])?(?P<cur>\$)?(?P<num>\d[\d,]*(?:\.\d+)?)\s?(?P<suffix>[KMB](?![a-z])|%|pts|bps|days)?")


def parse_number(text: str) -> float:
    m = _NUMBER.search(text.strip())
    if not m:
        raise ValueError(f"no number in {text!r}")
    value = float(m["num"].replace(",", ""))
    suffix = m["suffix"]
    value *= {"K": 1e3, "M": 1e6, "B": 1e9, "%": 0.01, "pts": 0.01}.get(suffix, 1.0)
    return -value if m["sign"] == "-" else value


@dataclass(frozen=True)
class Fact:
    fact_id: str
    label: str
    value: float
    kind: str
    display: str


class FactBook:
    def __init__(self, store: GovernedStore):
        self.store = store
        self.facts: dict[str, Fact] = {}

    def cite(self, label: str, value, kind: str, inputs: tuple[str, ...], formula: str) -> dict | None:
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            return None
        rounded = float(f"{float(value):.6g}")
        fact_id = self.store.register_derived(label, rounded, STORE_UNIT[kind], tuple(dict.fromkeys(inputs)), formula)
        return self._add(fact_id, label, rounded, kind)

    def cite_existing(self, fact_id: str, kind: str) -> dict:
        fact = self.store.get(fact_id)
        return self._add(fact_id, fact.label, float(fact.value), kind)

    def _add(self, fact_id: str, label: str, value: float, kind: str) -> dict:
        fact = Fact(fact_id, label, value, kind, fmt(value, kind))
        self.facts[fact_id] = fact
        return {"value": fact.display, "ref": f"q:{fact_id}"}
