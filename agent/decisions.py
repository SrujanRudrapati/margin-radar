"""Decision log and decision scorer (docs/SPEC.md Phase 6). Synthetic data — not Opendoor data.

The log is a DuckDB table `decision_log` in its own file (the run databases stay read-only). The scorer compares each
decision with the margin that was later realized in the alert's scope, using only data: the sold-cohort contribution
margin gap vs peer segments (the same leave-one-out peer comparison the detector uses). Estimated $ saved assumes that
acting stops the erosion on purchases made after the decision, until the week the gap became visible in margin.
"""
import math
import re
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from common.business import SAMPLE_SCALE_LABEL
from detector.config import MIN_SEGMENT_SAMPLE, WINDOW_WEEKS
from detector.governed import GovernedStore
from detector.peers import peer_residuals, rollup
from detector.rules import detect

DECISIONS = ("acted", "dismissed", "deferred")
KINDS = ("adverse_selection", "demand_softening", "reno_cost_drift", "portfolio_shift")
ALERT_ID = re.compile(r"^A[0-9A-Za-z]{1,16}$")
SCOPE = re.compile(r"^(M0[1-6]|B[1-3]|portfolio)$")
MAX_REASON = 500
VISIBLE_GAP = -0.005  # sold-cohort CM gap vs peers of -50 bps ...
VISIBLE_WEEKS = 2     # ... for 2 consecutive weeks counts as "visible in margin"
EXAMPLE = "(example) "
SAVED_LABEL = (f"estimated $ saved ({SAMPLE_SCALE_LABEL}); assumes acting stops the erosion on purchases made "
               "after the decision until the gap became visible in margin")


class DecisionLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._con() as con:
            con.execute("create table if not exists decision_log (alert_id varchar, decision varchar, reason varchar, "
                        "decided_week integer, scope varchar, kind varchar, ts timestamp)")

    def _con(self):
        return duckdb.connect(str(self.path))

    def record(self, alert_id: str, decision: str, reason: str, decided_week: int, scope: str, kind: str,
               ts: datetime | None = None) -> dict:
        if not isinstance(alert_id, str) or not ALERT_ID.match(alert_id):
            raise ValueError(f"invalid alert_id {alert_id!r}")
        if decision not in DECISIONS:
            raise ValueError(f"decision must be one of {DECISIONS}")
        if not isinstance(reason, str) or len(reason) > MAX_REASON:
            raise ValueError(f"reason must be text of at most {MAX_REASON} characters")
        if not isinstance(decided_week, int) or isinstance(decided_week, bool) or decided_week < 0:
            raise ValueError("decided_week must be a non-negative int")
        if not isinstance(scope, str) or not SCOPE.match(scope) or kind not in KINDS:
            raise ValueError("invalid scope or kind")
        row = {"alert_id": alert_id, "decision": decision, "reason": reason.strip(), "decided_week": decided_week,
               "scope": scope, "kind": kind, "ts": ts or datetime.now().replace(microsecond=0)}
        with self._con() as con:
            con.execute("insert into decision_log values (?, ?, ?, ?, ?, ?, ?)", list(row.values()))
        return row

    def list(self, decision: str | None = None, kind: str | None = None, scope: str | None = None) -> list[dict]:
        clauses, params = [], []
        for column, value in (("decision", decision), ("kind", kind), ("scope", scope)):
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)
        where = f"where {' and '.join(clauses)}" if clauses else ""
        with self._con() as con:
            frame = con.execute(f"select * from decision_log {where} order by decided_week, ts", params).fetchdf()
        return frame.to_dict("records")

    def clear_examples(self) -> None:
        with self._con() as con:
            con.execute("delete from decision_log where reason like ?", [EXAMPLE + "%"])


def savings_usd(erosion_bps: float, avoided_purchases_usd: float) -> float:
    return max(0.0, erosion_bps) / 1e4 * avoided_purchases_usd


def seed_examples(log: DecisionLog, store: GovernedStore) -> list[dict]:
    """Example decisions on the first alert episodes in the run (idempotent: replaces earlier examples)."""
    log.clear_examples()
    first: dict[tuple[str, str], tuple[int, str]] = {}
    for week in range(0, store.max_week + 1):
        for alert in detect(store, week).alerts:
            first.setdefault((alert.kind, alert.scope), (week, alert.alert_id))
    plans = {
        "adverse_selection": [("acted", 2, "Pricing widened the spread and added in-person inspection")],
        "reno_cost_drift": [("deferred", 0, "Waiting one more week of renovation data"),
                            ("acted", 3, "Re-baselined renovation estimates; in-person assessment required")],
        "demand_softening": [("dismissed", 1, "Judged a local listing-mix effect")],
        "portfolio_shift": [("deferred", 0, "Checking external drivers first")],
    }
    out = []
    for (kind, scope), (week, alert_id) in sorted(first.items(), key=lambda item: item[1][0]):
        for decision, lag, reason in plans[kind]:
            out.append(log.record(alert_id, decision, EXAMPLE + reason, min(week + lag, store.max_week), scope, kind))
    return out


def score_decisions(log: DecisionLog, store: GovernedStore) -> dict:
    as_of = store.max_week
    rows = []
    for d in log.list():
        rows.append(_score_one(store, d, as_of))
    acted_alerts = {r["alert_id"] for r in rows if r["decision"] == "acted"}
    saved = sum(r["estimated_saved_usd"] for r in rows if r["decision"] == "acted")
    return {"label": SAVED_LABEL, "as_of_week": as_of, "decisions": len(rows),
            "alerts_with_decisions": len({r["alert_id"] for r in rows}), "decisions_influenced": len(acted_alerts),
            "estimated_saved_usd": saved, "rows": rows}


def _score_one(store: GovernedStore, d: dict, as_of: int) -> dict:
    dimension = "market" if d["scope"].startswith("M") else ("band" if d["scope"].startswith("B") else "portfolio")
    gap, refs = _cm_gap(store, dimension, d["scope"], as_of)
    week = int(d["decided_week"])
    after = gap.loc[week:].dropna()
    visible = _visible_week(after)
    hold_weeks = _hold_weeks(store, dimension, d["scope"], as_of)
    realized = after.loc[week + hold_weeks:] if hold_weeks is not None else after.iloc[0:0]
    erosion_bps = None if realized.empty else float(-realized.median() * 1e4)
    end = visible if visible is not None else as_of + 1
    avoided = _purchases(store, dimension, d["scope"], week, end - 1) if end > week else 0.0
    saved = savings_usd(erosion_bps or 0.0, avoided) if d["decision"] == "acted" else 0.0
    not_avoided = savings_usd(erosion_bps or 0.0, avoided) if d["decision"] == "dismissed" else 0.0
    ids = []
    for label, value, unit in (("realized erosion bps", erosion_bps, "bps"), ("avoided purchases usd", avoided, "usd"),
                               ("estimated saved usd", saved, "usd")):
        if value is not None and math.isfinite(value):
            ids.append(store.register_derived(f"decision {d['alert_id']} {d['decision']} week {week} {label}",
                                              float(f"{value:.6g}"), unit, refs, "decision scorer"))
    return {**{k: d[k] for k in ("alert_id", "decision", "reason", "decided_week", "scope", "kind")},
            "ts": str(d["ts"]), "realized_erosion_bps": erosion_bps, "margin_visible_week": visible,
            "avoided_purchases_usd": avoided, "estimated_saved_usd": saved, "at_risk_not_avoided_usd": not_avoided,
            "ref_ids": ids}


def _cm_gap(store: GovernedStore, dimension: str, scope: str, as_of: int) -> tuple[pd.Series, tuple[str, ...]]:
    if dimension == "portfolio":
        return pd.Series(dtype=float), ()
    panel = store.panel("contribution_margin_pct", "segment", as_of, WINDOW_WEEKS, min_denominator=MIN_SEGMENT_SAMPLE)
    roll = rollup(peer_residuals(panel, dimension), dimension)
    return roll[roll["scope"] == scope].set_index("week")["residual"], (panel.query_id,)


def _visible_week(gap: pd.Series) -> int | None:
    below = (gap <= VISIBLE_GAP).astype(int)
    run = below.groupby((below != below.shift()).cumsum()).cumsum()
    hits = run[(below == 1) & (run >= VISIBLE_WEEKS)]
    return None if hits.empty else int(hits.index[0]) - VISIBLE_WEEKS + 1


def _hold_weeks(store: GovernedStore, dimension: str, scope: str, as_of: int) -> int | None:
    if dimension == "portfolio":
        return None
    days = _value(store, "hold_days_sum", dimension, scope, as_of, 13)
    sold = _value(store, "resales", dimension, scope, as_of, 13)
    return None if not days or not sold else math.ceil(days / sold / 7)


def _purchases(store: GovernedStore, dimension: str, scope: str, start: int, end: int) -> float:
    return _value(store, "acquisition_usd", dimension, scope, end, end - start + 1) or 0.0


def _value(store: GovernedStore, metric: str, level: str, scope: str, week: int, window: int) -> float | None:
    window = max(1, min(window, week + 1))
    panel = store.panel(metric, level, week, window)
    row = panel.values[(panel.values["scope"] == scope) & (panel.values["week"] == week)]
    value = row["value"].iloc[0] if len(row) else None
    return None if value is None else float(value)
