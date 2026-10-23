"""Decision log and decision scorer (docs/SPEC.md Phase 6). Synthetic data — not Opendoor data.

The log is a DuckDB table `decision_log` in its own file (the run databases stay read-only). The scorer compares each
decision with the margin that was later realized in the alert's scope, using only data: the sold-cohort contribution
margin gap vs peer segments (the same leave-one-out peer comparison the detector uses). Estimated $ saved assumes that
acting stops the erosion on purchases made after the decision, until the week the gap became visible in margin. The
synthetic data does not react to decisions, so the erosion measured after a decision is the no-action counterfactual;
on real data an effective action would hide its own savings. Erosion is in bps of resale price applied to purchase
dollars (a small, stated bias). One writer: the API process; do not run `make decisions` while the API is up.
"""
import math
import re
from datetime import datetime, timezone
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
               "after the decision until the gap became visible in margin; the synthetic data does not react to "
               "decisions, so measured erosion is the no-action counterfactual")


class DecisionLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._con() as con:
            con.execute("create table if not exists decision_log (alert_id varchar, decision varchar, reason varchar, "
                        "decided_week integer, scope varchar, kind varchar, ts timestamp, is_example boolean)")

    def _con(self):
        return duckdb.connect(str(self.path))

    def record(self, alert_id: str, decision: str, reason: str, decided_week: int, scope: str, kind: str,
               ts: datetime | None = None, is_example: bool = False) -> dict:
        if not isinstance(alert_id, str) or not ALERT_ID.match(alert_id):
            raise ValueError(f"invalid alert_id {alert_id!r}")
        if decision not in DECISIONS:
            raise ValueError(f"decision must be one of {DECISIONS}")
        reason = reason.strip() if isinstance(reason, str) else reason
        if not isinstance(reason, str) or not reason or len(reason) > MAX_REASON:
            raise ValueError(f"reason must be non-empty text of at most {MAX_REASON} characters")
        if not isinstance(decided_week, int) or isinstance(decided_week, bool) or decided_week < 0:
            raise ValueError("decided_week must be a non-negative int")
        if not isinstance(scope, str) or not SCOPE.match(scope) or kind not in KINDS:
            raise ValueError("invalid scope or kind")
        row = {"alert_id": alert_id, "decision": decision, "reason": reason, "decided_week": decided_week,
               "scope": scope, "kind": kind, "ts": ts or datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None),
               "is_example": bool(is_example)}
        with self._con() as con:
            con.execute("insert into decision_log values (?, ?, ?, ?, ?, ?, ?, ?)", list(row.values()))
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
            con.execute("delete from decision_log where is_example")


def savings_usd(erosion_bps: float, avoided_purchases_usd: float) -> float:
    return max(0.0, erosion_bps) / 1e4 * avoided_purchases_usd


def alert_episodes(store: GovernedStore) -> dict[str, dict]:
    """alert_id -> {kind, scope, first_week, last_week} for every alert the detector raised in this run."""
    out: dict[str, dict] = {}
    for week in range(0, store.max_week + 1):
        for alert in detect(store, week).alerts:
            e = out.setdefault(alert.alert_id, {"kind": alert.kind, "scope": alert.scope, "first_week": week})
            e["last_week"] = week
    return out


def log_decision(log: DecisionLog, store: GovernedStore, alert_id: str, decision: str, reason: str, decided_week: int,
                 episodes: dict[str, dict] | None = None) -> dict:
    """Record a decision on a real alert: scope and kind come from the alert, and the decision week must fall
    between the alert's first detection and the last week of data."""
    episodes = episodes if episodes is not None else alert_episodes(store)
    alert = episodes.get(alert_id)
    if alert is None:
        raise ValueError(f"unknown alert {alert_id!r}")
    if not isinstance(decided_week, int) or not alert["first_week"] <= decided_week <= store.max_week:
        raise ValueError(f"decided_week must be between the alert's first week ({alert['first_week']}) and "
                         f"{store.max_week}")
    return log.record(alert_id, decision, reason, decided_week, alert["scope"], alert["kind"])


def seed_examples(log: DecisionLog, store: GovernedStore) -> list[dict]:
    """Example decisions on the first alert episodes in the run (idempotent: replaces earlier examples only)."""
    log.clear_examples()
    episodes = alert_episodes(store)
    plans = {
        "adverse_selection": [("acted", 2, "Pricing widened the spread and added in-person inspection")],
        "reno_cost_drift": [("deferred", 0, "Waiting one more week of renovation data"),
                            ("acted", 3, "Re-baselined renovation estimates; in-person assessment required")],
        "demand_softening": [("dismissed", 1, "Judged a local listing-mix effect")],
        "portfolio_shift": [("deferred", 0, "Checking external drivers first")],
    }
    out = []
    for alert_id, e in sorted(episodes.items(), key=lambda item: item[1]["first_week"]):
        for decision, lag, reason in plans[e["kind"]]:
            week = min(e["first_week"] + lag, store.max_week)
            out.append(log.record(alert_id, decision, EXAMPLE + reason, week, e["scope"], e["kind"], is_example=True))
    return out


def score_decisions(log: DecisionLog, store: GovernedStore, episodes: dict[str, dict] | None = None) -> dict:
    as_of = store.max_week
    episodes = episodes if episodes is not None else alert_episodes(store)
    decisions = log.list()
    first_acted = {}
    for d in decisions:  # list() is ordered by week, then time: the first acted row per alert is the one that counts
        if d["decision"] == "acted":
            first_acted.setdefault(d["alert_id"], id(d))
    rows = [_score_one(store, d, as_of, episodes.get(d["alert_id"]), counted=first_acted.get(d["alert_id"]) == id(d))
            for d in decisions]
    counted = [r for r in rows if r["counted"]]
    return {"label": SAVED_LABEL, "as_of_week": as_of, "decisions": len(rows),
            "alerts_with_decisions": len({r["alert_id"] for r in rows}),
            "decisions_influenced": len({r["alert_id"] for r in counted}),
            "decisions_influenced_means": "alerts with at least one acted decision",
            "estimated_saved_usd": sum(r["estimated_saved_usd"] for r in counted), "rows": rows}


def _score_one(store: GovernedStore, d: dict, as_of: int, episode: dict | None, counted: bool) -> dict:
    dimension = "market" if d["scope"].startswith("M") else ("band" if d["scope"].startswith("B") else "portfolio")
    gap, gap_refs = _cm_gap(store, dimension, d["scope"], as_of)
    start = int(d["decided_week"]) if episode is None else max(int(d["decided_week"]), episode["first_week"])
    after = gap.loc[start:]
    visible = visible_week(after)
    hold_weeks, hold_refs = _hold_weeks(store, dimension, d["scope"], as_of)
    realized = after.loc[start + hold_weeks:].dropna() if hold_weeks is not None else after.iloc[0:0]
    erosion_bps = None if realized.empty else float(-realized.median() * 1e4)
    end = visible if visible is not None else as_of + 1
    avoided, purchase_refs = _purchases(store, dimension, d["scope"], start, end - 1) if end > start else (0.0, ())
    value = savings_usd(erosion_bps or 0.0, avoided)
    saved = value if d["decision"] == "acted" and counted else 0.0
    not_avoided = value if d["decision"] == "dismissed" else 0.0
    label = f"decision {d['alert_id']} {d['decision']} week {d['decided_week']}"
    ids = []
    erosion_id = _fact(store, f"{label} realized erosion bps", erosion_bps, "bps", gap_refs + hold_refs, "scorer: erosion")
    purchases_id = _fact(store, f"{label} avoided purchases usd", avoided, "usd", purchase_refs, "scorer: purchases")
    ids += [i for i in (erosion_id, purchases_id) if i]
    saved_inputs = tuple(i for i in (erosion_id, purchases_id) if i)
    if saved_inputs:
        ids.append(_fact(store, f"{label} estimated saved usd", saved, "usd", saved_inputs, "scorer: erosion x purchases"))
    return {**{k: d[k] for k in ("alert_id", "decision", "reason", "decided_week", "scope", "kind")},
            "is_example": bool(d.get("is_example")), "ts": str(d["ts"]), "counted": counted,
            "realized_erosion_bps": erosion_bps, "margin_visible_week": visible, "window_start_week": start,
            "avoided_purchases_usd": avoided, "estimated_saved_usd": saved, "at_risk_not_avoided_usd": not_avoided,
            "ref_ids": ids}


def _fact(store: GovernedStore, label: str, value, unit: str, inputs: tuple[str, ...], formula: str) -> str | None:
    if value is None or not math.isfinite(value) or not inputs:
        return None
    return store.register_derived(label, float(f"{value:.6g}"), unit, tuple(dict.fromkeys(inputs)), formula)


def _cm_gap(store: GovernedStore, dimension: str, scope: str, as_of: int) -> tuple[pd.Series, tuple[str, ...]]:
    if dimension == "portfolio":
        return pd.Series(dtype=float), ()
    panel = store.panel("contribution_margin_pct", "segment", as_of, WINDOW_WEEKS, min_denominator=MIN_SEGMENT_SAMPLE)
    roll = rollup(peer_residuals(panel, dimension), dimension)
    return roll[roll["scope"] == scope].set_index("week")["residual"], (panel.query_id,)


def visible_week(gap: pd.Series) -> int | None:
    """First week of the first run of VISIBLE_WEEKS consecutive weeks with gap <= VISIBLE_GAP (missing weeks break runs)."""
    if gap.empty:
        return None
    full = gap.reindex(range(int(gap.index.min()), int(gap.index.max()) + 1))
    streak = 0
    for week, value in full.items():
        streak = streak + 1 if pd.notna(value) and value <= VISIBLE_GAP else 0
        if streak >= VISIBLE_WEEKS:
            return int(week) - VISIBLE_WEEKS + 1
    return None


def _hold_weeks(store: GovernedStore, dimension: str, scope: str, as_of: int) -> tuple[int | None, tuple[str, ...]]:
    if dimension == "portfolio":
        return None, ()
    days, a = _value(store, "hold_days_sum", dimension, scope, as_of, 13)
    sold, b = _value(store, "resales", dimension, scope, as_of, 13)
    return (None if not days or not sold else math.ceil(days / sold / 7)), (a, b)


def _purchases(store: GovernedStore, dimension: str, scope: str, start: int, end: int) -> tuple[float, tuple[str, ...]]:
    value, ref = _value(store, "acquisition_usd", dimension, scope, end, end - start + 1)
    return (value or 0.0), (ref,)


def _value(store: GovernedStore, metric: str, level: str, scope: str, week: int, window: int) -> tuple[float | None, str]:
    window = max(1, min(window, week + 1))
    panel = store.panel(metric, level, week, window)
    row = panel.values[(panel.values["scope"] == scope) & (panel.values["week"] == week)]
    value = row["value"].iloc[0] if len(row) else None
    return (None if value is None else float(value)), panel.query_id
