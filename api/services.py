"""Dashboard data services: thin, read-only views over the governed store, detector, briefs and eval artifacts.

One run database is opened per request (the run toggle); runs are never queried together and ground truth is never
read (lead-time markers come from eval/lead_time.json). Synthetic data — not Opendoor data.
"""
import dataclasses
import json
import math
import re
import threading
from pathlib import Path

from agent.decisions import DecisionLog, log_decision, score_decisions
from common.banner import SYNTHETIC_BANNER
from common.business import SAMPLE_SCALE_LABEL
from detector.config import MIN_SEGMENT_SAMPLE, WINDOW_WEEKS
from detector.drift import DriftScore, score
from detector.governed import GovernedStore
from detector.impact import rank_actions
from detector.peers import peer_residuals, rollup
from detector.rules import TRIGGERS, detect

RUNS = ("injected", "control")
DIMENSIONS = ("market", "band")
DEFAULT_WEEK = 40
COHORT_WEEKS = (30, 33)


def _clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value


class Services:
    def __init__(self, data_dir: Path, briefs_dirs: list[Path], eval_dir: Path, decisions_db: Path):
        self.data_dir, self.briefs_dirs, self.eval_dir = Path(data_dir), [Path(p) for p in briefs_dirs], Path(eval_dir)
        self.decisions = DecisionLog(decisions_db)
        self._stores: dict[str, GovernedStore] = {}
        self._episodes: dict[str, list[dict]] = {}
        self._lock = threading.Lock()  # DuckDB connections are not shared across threads concurrently
        self.warmed = threading.Event()  # set once both runs' alert episodes are cached (see warm)

    # --- plumbing -------------------------------------------------------------------------------------------
    def _store(self, run: str) -> GovernedStore:
        if run not in RUNS:
            raise ValueError(f"run must be one of {RUNS}")
        if run not in self._stores:
            self._stores[run] = GovernedStore(str(self.data_dir / f"radar_{run}.duckdb"), run)
        return self._stores[run]

    def _week(self, store: GovernedStore, week: int) -> int:
        if not 0 <= int(week) <= store.max_week:
            raise ValueError(f"week must be between 0 and {store.max_week}")
        return int(week)

    def _scopes(self, store: GovernedStore, level: str) -> list[str]:
        panel = store.panel("offers", level, store.max_week, 1)
        return sorted(panel.values["scope"].unique())

    # --- endpoints ------------------------------------------------------------------------------------------
    def meta(self) -> dict:
        with self._lock:
            store = self._store("injected")
            return {"banner": SYNTHETIC_BANNER, "sample_scale_label": SAMPLE_SCALE_LABEL, "runs": list(RUNS),
                    "max_week": store.max_week, "default_week": DEFAULT_WEEK, "trigger_metrics": list(TRIGGERS),
                    "markets": self._scopes(store, "market"), "bands": self._scopes(store, "band"),
                    "week_starts": [store.week_start(w) for w in range(store.max_week + 1)],
                    "brief_weeks": [b["week"] for b in self.briefs()["briefs"]]}

    def radar(self, run: str, week: int) -> dict:
        with self._lock:
            store = self._store(run)
            week = self._week(store, week)
            result = detect(store, week)
            ranked = rank_actions(result, store)
            alerts = {a.alert_id: a for a in result.alerts}
            cm = store.panel("contribution_margin_pct", "portfolio", week, min(13, week + 1))
            cm_row = cm.values[cm.values["week"] == week]["value"]
            quantified = [r.impact for r in ranked if r.impact.basis != "sensitivity"]
            actions = []
            for r in ranked[:3]:
                a = alerts[r.alert_id]
                s = a.signals[0]
                actions.append({"rank": r.rank, "alert_id": r.alert_id, "kind": r.kind, "scope": r.scope,
                                "dimension": a.dimension, "onset_week": a.onset_week, "action": r.action, "owner": r.owner,
                                "signal": {"metric": s.metric, "direction": s.direction, "score": s.z, "gap": s.residual},
                                "impact": dataclasses.asdict(r.impact)})
            return _clean({
                "banner": SYNTHETIC_BANNER, "run": run, "week": week, "week_start": store.week_start(week),
                "global_abstention": any(x.scope == "all" for x in result.abstentions),
                "kpis": {"cm_pct": None if cm_row.empty or cm_row.iloc[0] is None else float(cm_row.iloc[0]),
                         "cm_window_weeks": min(13, week + 1),
                         "usd_at_risk_mid": sum(i.usd_mid or 0 for i in quantified),
                         "portfolio_cm_bps_mid": sum(i.portfolio_cm_bps_mid or 0 for i in quantified),
                         "active_alerts": len(result.alerts), "more_actions": max(0, len(ranked) - 3)},
                "actions": actions,
                "watch": [dataclasses.asdict(w) for w in result.watch],
            })

    def heatmap(self, run: str, week: int, metric: str) -> dict:
        if metric not in TRIGGERS:
            raise ValueError(f"metric must be one of {list(TRIGGERS)}")
        with self._lock:
            store = self._store(run)
            week = self._week(store, week)
            panel = store.panel(metric, "segment", week, WINDOW_WEEKS, min_denominator=MIN_SEGMENT_SAMPLE)
            res = peer_residuals(panel, "market")
            cells = []
            for (segment, market, band, product), frame in res.groupby(["segment", "market", "band", "product"]):
                result = score(frame.set_index("week")["residual"], week, metric)
                fired = isinstance(result, DriftScore) and result.fired
                cells.append({"segment": segment, "market": market, "band": band, "product": product,
                              "score": result.z_latest if isinstance(result, DriftScore) else None,
                              "direction": result.direction if isinstance(result, DriftScore) else None,
                              "fired": fired, "risk_direction": TRIGGERS[metric][0]})
            return _clean({"banner": SYNTHETIC_BANNER, "run": run, "week": week, "metric": metric,
                           "note": "segment vs the same band and product in other markets; uncalibrated score",
                           "cells": cells})

    def drilldown(self, run: str, metric: str, dimension: str, scope: str) -> dict:
        if metric not in TRIGGERS:
            raise ValueError(f"metric must be one of {list(TRIGGERS)}")
        if dimension not in DIMENSIONS:
            raise ValueError(f"dimension must be one of {DIMENSIONS}")
        with self._lock:
            store = self._store(run)
            if scope not in self._scopes(store, dimension):
                raise ValueError(f"unknown {dimension} {scope!r}")
            last = store.max_week
            segment = store.panel(metric, "segment", last, WINDOW_WEEKS, min_denominator=MIN_SEGMENT_SAMPLE)
            roll = rollup(peer_residuals(segment, dimension), dimension)
            own = roll[roll["scope"] == scope].set_index("week").sort_index()
            scoped = store.panel(metric, dimension, last, WINDOW_WEEKS, min_denominator=MIN_SEGMENT_SAMPLE)
            values = scoped.values[scoped.values["scope"] == scope].set_index("week")["value"]
            weeks = list(own.index)
            se = own["se"].fillna(0.0)
            scores = []
            for w in weeks:
                r = score(own["residual"], w, metric, se)
                scores.append(r.z_latest if isinstance(r, DriftScore) else None)
            episodes = [e for e in self._all_episodes(run, store) if e["scope"] == scope]
        truth = None
        if run == "injected":
            markers = self._read_json(self.eval_dir / "lead_time.json") or {}
            truth = next((m for m in markers.get("scenarios", []) if m["scope"] == scope), None)
        return _clean({"banner": SYNTHETIC_BANNER, "run": run, "metric": metric, "dimension": dimension, "scope": scope,
                       "weeks": [int(w) for w in weeks], "value": [_f(values.get(w)) for w in weeks],
                       "peer": [_f(x) for x in own["peer_level"]], "gap": [_f(x) for x in own["residual"]],
                       "score": scores, "alerts": episodes, "truth": truth,
                       "query_ids": [segment.query_id, scoped.query_id]})

    def _all_episodes(self, run: str, store: GovernedStore) -> list[dict]:
        if run not in self._episodes:
            self._episodes[run] = _detect_episodes(store)
        return self._episodes[run]

    def cohort(self, run: str, week: int, level: str, scope: str, start: int, end: int) -> dict:
        with self._lock:
            store = self._store(run)
            week = self._week(store, week)
            panel = store.cohort_curve(level, scope, int(start), int(end), week)
            frame = panel.values
            return _clean({"banner": SYNTHETIC_BANNER, "run": run, "week": week, "level": level, "scope": scope,
                           "close_weeks": [int(start), int(end)], "query_id": panel.query_id,
                           "cohort_homes": int(frame["n_homes"].iloc[0]),
                           "points": [{"sold_share": float(r.sold_share), "cm_pct": _f(r.cm_pct)} for r in frame.itertuples()]})

    def briefs(self) -> dict:
        out = {}
        for folder in self.briefs_dirs:
            for path in sorted(folder.glob("week_*.json")):
                if ".invalid" in path.name or not re.match(r"week_\d+\.json$", path.name):
                    continue
                data = json.loads(path.read_text())
                out.setdefault(data["week"], {"week": data["week"], "status": data["status"], "model": data.get("model"),
                                              "source": folder.name})
        return {"banner": SYNTHETIC_BANNER, "briefs": [out[w] for w in sorted(out)]}

    def brief(self, week: int) -> dict | None:
        for folder in self.briefs_dirs:
            path = folder / f"week_{int(week):02d}.json"
            if path.exists():
                data = json.loads(path.read_text())
                md = path.with_suffix(".md")
                return {**data, "markdown": md.read_text() if md.exists() else None}
        return None

    def evaluation(self) -> dict:
        results = self._read_json(self.eval_dir / "results.json")
        if results is None:
            return {"banner": SYNTHETIC_BANNER, "available": False}
        return {"banner": SYNTHETIC_BANNER, "available": True, **results,
                "lead_time": self._read_json(self.eval_dir / "lead_time.json")}

    def decisions_view(self, decision: str | None = None, kind: str | None = None, scope: str | None = None) -> dict:
        rows = self.decisions.list(decision=decision, kind=kind, scope=scope)
        with self._lock:
            store = self._store("injected")
            report = score_decisions(self.decisions, store, self._episode_index(store))
        return _clean({"banner": SYNTHETIC_BANNER, "decisions": [{**r, "ts": str(r["ts"])} for r in rows],
                       "score": {k: v for k, v in report.items() if k != "rows"}, "scored_rows": report["rows"]})

    def add_decision(self, payload: dict) -> dict:
        with self._lock:
            store = self._store("injected")
            row = log_decision(self.decisions, store, payload["alert_id"], payload["decision"], payload["reason"],
                               payload["decided_week"], self._episode_index(store))
        return {**row, "ts": str(row["ts"])}

    def warm(self) -> None:
        """Replay the detector over every week of both runs (~20 s each) so no request pays for it. Uses its own
        read-only connection, so requests are not blocked; the lock is held only to store the result."""
        replayed = {}
        for run in RUNS:
            with GovernedStore(str(self.data_dir / f"radar_{run}.duckdb"), run) as store:
                replayed[run] = _detect_episodes(store)
        with self._lock:
            for run, episodes in replayed.items():
                self._episodes.setdefault(run, episodes)
        self.warmed.set()

    def _episode_index(self, store: GovernedStore) -> dict[str, dict]:
        return {e["alert_id"]: e for e in self._all_episodes("injected", store)}

    @staticmethod
    def _read_json(path: Path) -> dict | None:
        return json.loads(path.read_text()) if path.exists() else None


def _detect_episodes(store: GovernedStore) -> list[dict]:
    episodes: dict[str, dict] = {}
    for week in range(store.max_week + 1):
        for a in detect(store, week).alerts:
            e = episodes.setdefault(a.alert_id, {"alert_id": a.alert_id, "kind": a.kind, "scope": a.scope,
                                                 "onset_week": a.onset_week, "first_week": week})
            e["last_week"] = week
    return list(episodes.values())


def _f(x):
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None
