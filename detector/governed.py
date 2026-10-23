"""Governed, single-database query layer. Synthetic data — not Opendoor data.

A GovernedStore opens exactly one run's DuckDB file read-only. Metric definitions are parsed from the
dbt semantic-layer YAML (one source of truth); SQL is built from whitelisted names only. Every panel
gets a deterministic query ID and every derived number must cite panels or facts by ID.
"""
from __future__ import annotations

import hashlib
import json
import math
import numbers
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

import duckdb
import pandas as pd
import yaml

Level = Literal["segment", "market", "band", "portfolio"]
Unit = Literal["usd", "bps", "pct", "count", "days", "ratio"]

SEMANTIC_DIR = Path(__file__).resolve().parents[1] / "dbt_project" / "models" / "semantic"
MART = "main.mart_segment_week"
DEFAULT_MIN_DENOMINATOR = 10
MIN_DENOMINATOR: dict[str, int] = {"contract_rate": 30, "first_offer_rate": 20, "reno_overrun_pct": 10}
SCOPE_SQL: dict[str, str] = {"segment": "segment", "market": "market", "band": "band", "portfolio": "'portfolio'"}
UNITS = frozenset(("usd", "bps", "pct", "count", "days", "ratio"))
# Point-in-time state columns (nonzero in every week after the data ends); excluded from max_week.
STATE_COLUMNS = frozenset(("awaiting_offer", "unsold_inventory_usd"))
RUN_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_NAME = r"([A-Za-z_]\w*)"
# The four derived forms the semantic layer uses; anything else fails loudly.
_DERIVED_FORMS = (
    (re.compile(rf"^{_NAME} / {_NAME} \* 7$"), lambda a, b: f"({a}) / nullif({b}, 0) * 7"),
    (re.compile(rf"^{_NAME} / {_NAME} - 1$"), lambda a, b: f"({a}) / nullif({b}, 0) - 1"),
    (re.compile(rf"^\({_NAME} / {_NAME} - 1\) \* 10000$"), lambda a, b: f"(({a}) / nullif({b}, 0) - 1) * 10000"),
    (re.compile(rf"^{_NAME} / {_NAME} / {_NAME} \* 10000$"),
     lambda a, b, c: f"({a}) / nullif({b}, 0) / nullif({c}, 0) * 10000"),
)
_SIMPLE_KEYS = {"measure"}
_RATIO_KEYS = {"numerator", "denominator"}
_DERIVED_KEYS = {"expr", "metrics"}


@dataclass(frozen=True)
class MetricPanel:
    query_id: str
    metric: str
    run_id: str
    level: Level
    as_of_week: int
    window_weeks: int
    # values columns: scope, week, value, denominator (+ market, band, product when level == "segment").
    # value is None below the sample threshold, and for weeks < window_weeks - 1 (partial windows), whose
    # denominator is also None. denominator is the windowed sample-size count (meta.sample_size), not
    # necessarily the ratio's formula denominator; None for metrics without a sample_size.
    values: pd.DataFrame
    sql: str


@dataclass(frozen=True)
class DerivedFact:
    fact_id: str
    label: str
    value: float
    unit: Unit
    inputs: tuple[str, ...]
    formula: str


@dataclass(frozen=True)
class _Metric:
    name: str
    type: str
    params: dict
    sample_size: str | None
    role: str | None = None


def _is_int(x) -> bool:
    return isinstance(x, numbers.Integral) and not isinstance(x, bool)


def _name_of(ref) -> str:
    if isinstance(ref, str):
        return ref
    if isinstance(ref, dict) and set(ref) == {"name"}:
        return ref["name"]
    raise ValueError(f"unsupported metric reference: {ref!r}")


def load_definitions(semantic_dir: Path = SEMANTIC_DIR) -> tuple[dict[str, _Metric], frozenset[str]]:
    """Parse metrics and non-additive measures from the semantic YAML; reject any form we cannot map."""
    metrics_doc = yaml.safe_load((semantic_dir / "metrics.yml").read_text())
    model_doc = yaml.safe_load((semantic_dir / "segment_week.yml").read_text())
    non_additive = frozenset(
        m["name"] for sm in model_doc["semantic_models"] for m in sm["measures"] if m.get("non_additive_dimension")
    )
    defs: dict[str, _Metric] = {}
    for raw in metrics_doc["metrics"]:
        name, kind, params = raw["name"], raw["type"], raw.get("type_params", {})
        allowed = {"simple": _SIMPLE_KEYS, "ratio": _RATIO_KEYS, "derived": _DERIVED_KEYS}.get(kind)
        if allowed is None or set(params) - allowed or set(raw) - {"name", "type", "type_params", "config", "description", "label"}:
            raise ValueError(f"metric {name!r}: unsupported definition ({kind}, {sorted(params)})")
        sample = (raw.get("config", {}).get("meta") or {}).get("sample_size")
        if kind != "simple" and not sample:
            raise ValueError(f"metric {name!r}: non-simple metric needs meta.sample_size")
        defs[name] = _Metric(name, kind, params, sample, (raw.get("config", {}).get("meta") or {}).get("role"))
    for d in defs.values():
        if d.type == "derived":
            _derived_sql_parts(d, defs)  # validate form eagerly
    return defs, non_additive


def _derived_sql_parts(d: _Metric, defs: dict[str, _Metric]) -> tuple[list[str], object]:
    declared = [_name_of(m) for m in d.params["metrics"]]
    expr = " ".join(d.params["expr"].split())
    for pattern, build in _DERIVED_FORMS:
        match = pattern.match(expr)
        if match:
            names = list(match.groups())
            unknown = [n for n in names if n not in declared or n not in defs]
            if unknown:
                raise ValueError(f"metric {d.name!r}: expression uses undeclared metrics {unknown}")
            return names, build
    raise ValueError(f"metric {d.name!r}: unsupported derived expression {d.params['expr']!r}")


def _metric_sql(name: str, defs: dict[str, _Metric], col) -> str:
    d = defs[name]
    if d.type == "simple":
        return col(_name_of(d.params["measure"]))
    if d.type == "ratio":
        num, den = (_metric_sql(_name_of(d.params[k]), defs, col) for k in ("numerator", "denominator"))
        return f"({num}) / nullif({den}, 0)"
    names, build = _derived_sql_parts(d, defs)
    return build(*(_metric_sql(n, defs, col) for n in names))


def _measures_of(name: str, defs: dict[str, _Metric]) -> list[str]:
    d = defs[name]
    if d.type == "simple":
        return [_name_of(d.params["measure"])]
    if d.type == "ratio":
        subs = [_name_of(d.params["numerator"]), _name_of(d.params["denominator"])]
    else:
        subs = _derived_sql_parts(d, defs)[0]
    return [m for s in subs for m in _measures_of(s, defs)]


class GovernedStore:
    def __init__(self, db_path: str, run_id: str, log_path: str | None = None):
        if not isinstance(run_id, str) or not RUN_ID_RE.match(run_id):
            raise ValueError(f"invalid run_id {run_id!r}")
        if not Path(db_path).is_file():
            raise ValueError(f"unknown run: no database at {db_path}")
        self.run_id = run_id
        self._log_path = Path(log_path) if log_path else None
        self._defs, self._non_additive = load_definitions()
        self._items: dict[str, MetricPanel | DerivedFact] = {}
        self._frames: dict[str, pd.DataFrame] = {}  # private frames behind panel query IDs
        self._con = duckdb.connect(db_path, read_only=True)
        try:
            self._check_mart()
            self.max_week = self._find_max_week()
        except Exception:
            self._con.close()
            raise

    def _check_mart(self) -> None:
        try:
            columns = {r[0] for r in self._con.execute(f"describe {MART}").fetchall()}
        except duckdb.Error as exc:
            raise ValueError(f"{MART} not found in database") from exc
        needed = {c for n in self._defs for c in _measures_of(n, self._defs)}
        needed |= {d.sample_size for d in self._defs.values() if d.sample_size}
        missing = needed - columns
        if missing:
            raise ValueError(f"mart lacks columns {sorted(missing)}")

    def _find_max_week(self) -> int:
        """Last week with any event activity: max week where any event-count/amount measure is
        non-zero (state columns such as awaiting_offer stay nonzero after the data ends, so they are excluded)."""
        cols = sorted({m for n, d in self._defs.items() if d.type == "simple" for m in _measures_of(n, self._defs)}
                      - self._non_additive - STATE_COLUMNS)
        active = " or ".join(f"coalesce({c}, 0) <> 0" for c in cols)
        week = self._con.execute(f"select max(week) from {MART} where {active}").fetchone()[0]
        if week is None:
            raise ValueError(f"{MART} has no event data")
        return int(week)

    def metrics(self, role: str | None = None) -> tuple[str, ...]:
        return tuple(sorted(n for n, d in self._defs.items() if role is None or d.role == role))

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> GovernedStore:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _build_sql(self, metric: str, level: str, as_of: int, window: int, start: int, floor: int) -> str:
        d = self._defs[metric]
        measures = sorted(set(_measures_of(metric, self._defs)) | ({d.sample_size} if d.sample_size else set()))
        agg_cols = ", ".join(f"cast(sum({m}) as double) as {m}" for m in measures)
        frame = f"over (partition by scope order by week rows between {window - 1} preceding and current row)"
        win_cols = ", ".join(
            m if m in self._non_additive else f"sum({m}) {frame} as {m}" for m in measures
        )
        value = _metric_sql(metric, self._defs, lambda m: m)
        if d.sample_size:
            value = f"case when {d.sample_size} < {floor} then null else {value} end"
            denominator = d.sample_size
        else:
            denominator = "null"
        if any(m not in self._non_additive for m in measures):  # partial windows are not comparable
            ramp = f"week < {window - 1}"
            value, denominator = f"case when {ramp} then null else {value} end", f"case when {ramp} then null else {denominator} end"
        dims = ", market, band, product" if level == "segment" else ""
        return (
            f"with agg as (select {SCOPE_SQL[level]} as scope, week{dims}, {agg_cols} from {MART} "
            f"where week <= {as_of} group by all), "
            f"win as (select scope, week{dims}, {win_cols} from agg) "
            f"select scope, week{dims}, {value} as value, {denominator} as denominator from win "
            f"where week >= {start} order by scope, week"
        )

    def panel(self, metric: str, level: Level, as_of_week: int, window_weeks: int = 4, start_week: int = 0,
              min_denominator: int | None = None) -> MetricPanel:
        if not isinstance(metric, str) or metric not in self._defs:
            raise ValueError(f"unknown metric {metric!r}")
        if not isinstance(level, str) or level not in SCOPE_SQL:
            raise ValueError(f"unknown level {level!r}")
        if not all(_is_int(i) for i in (as_of_week, window_weeks, start_week)):
            raise ValueError("as_of_week, window_weeks and start_week must be ints")
        as_of_week, window_weeks, start_week = int(as_of_week), int(window_weeks), int(start_week)
        if window_weeks < 1 or start_week < 0 or as_of_week < start_week:
            raise ValueError("need window_weeks >= 1 and 0 <= start_week <= as_of_week")
        if as_of_week > self.max_week:
            raise ValueError(f"as_of_week {as_of_week} is beyond the last week with data ({self.max_week})")
        if min_denominator is not None and not (_is_int(min_denominator) and min_denominator >= 0):
            raise ValueError("min_denominator must be a non-negative int or None")
        floor = int(min_denominator) if min_denominator is not None else MIN_DENOMINATOR.get(metric, DEFAULT_MIN_DENOMINATOR)
        sql = self._build_sql(metric, level, as_of_week, window_weeks, start_week, floor)
        key = "|".join(map(str, (self.run_id, metric, level, window_weeks, start_week, as_of_week, floor, sql)))
        query_id = "Q" + hashlib.sha256(key.encode()).hexdigest()[:10]
        if query_id in self._items:
            return replace(self._items[query_id], values=self._frames[query_id].copy())  # type: ignore[type-var]
        frame = self._con.execute(sql).fetchdf()
        frame["value"] = frame["value"].astype(object).where(frame["value"].notna(), None)
        frame["denominator"] = frame["denominator"].astype(object).where(frame["denominator"].notna(), None)
        panel = MetricPanel(query_id, metric, self.run_id, level, as_of_week, window_weeks, frame, sql)
        self._items[query_id], self._frames[query_id] = panel, frame.copy()
        self._log({"kind": "panel", "id": query_id, "metric": metric, "run_id": self.run_id, "level": level,
                   "window_weeks": window_weeks, "start_week": start_week, "as_of_week": as_of_week, "sql": sql,
                   **_summary(frame)})
        return replace(panel, values=frame.copy())

    def register_derived(self, label: str, value: float, unit: str, inputs: tuple[str, ...], formula: str) -> str:
        if unit not in UNITS:
            raise ValueError(f"unknown unit {unit!r}")
        if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value):
            raise ValueError(f"derived value must be a finite number, got {value!r}")
        unknown = [i for i in inputs if i not in self._items]
        if unknown:
            raise ValueError(f"derived fact cites unregistered inputs {unknown}")
        fact_id = "D" + hashlib.sha256(f"{label}|{unit}|{formula}|{'|'.join(inputs)}".encode()).hexdigest()[:10]
        fact = DerivedFact(fact_id, label, value, unit, tuple(inputs), formula)  # type: ignore[arg-type]
        existing = self._items.get(fact_id)
        if existing is not None:
            if existing != fact:
                raise ValueError(f"fact {fact_id} already registered with a different label/value/unit")
            return fact_id
        self._items[fact_id] = fact
        self._log({"kind": "derived", "id": fact_id, "label": label, "value": value, "unit": unit,
                   "inputs": list(inputs), "formula": formula})
        return fact_id

    def get(self, ref_id: str) -> MetricPanel | DerivedFact:
        if ref_id not in self._items:
            raise ValueError(f"unknown reference {ref_id!r}")
        item = self._items[ref_id]
        return replace(item, values=self._frames[ref_id].copy()) if isinstance(item, MetricPanel) else item

    def all(self) -> tuple[MetricPanel | DerivedFact, ...]:
        return tuple(self.get(i) for i in self._items)

    def _log(self, record: dict) -> None:
        if self._log_path is None:
            return
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._log_path.open("a") as fh:
            fh.write(json.dumps(record, default=str) + "\n")


def _summary(frame: pd.DataFrame) -> dict:
    values = [v for v in frame["value"] if v is not None]
    return {"n_rows": len(frame), "n_null": len(frame) - len(values),
            "min": min(values) if values else None, "max": max(values) if values else None}
