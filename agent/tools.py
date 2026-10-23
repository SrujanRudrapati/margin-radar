"""The brief agent's tools: get_alerts, query_metric, compare_segments, cohort_curve (docs/SPEC.md Phase 4).

Each tool reads one run's database through the governed store, with as_of_week fixed by the caller (the model
cannot change the week or the run). Every number in a result is a cited fact: {"value": display, "ref": "q:ID"}.
Synthetic data — not Opendoor data.
"""
from common.banner import SYNTHETIC_BANNER
from common.business import SAMPLE_SCALE_LABEL
from detector.config import ADVERSE_SELECTION_SHORTFALL, MIN_SEGMENT_SAMPLE, WINDOW_WEEKS
from detector.drift import DriftScore, score
from detector.governed import GovernedStore
from detector.impact import Impact, RankedAction, rank_actions
from detector.peers import peer_residuals, rollup
from detector.rules import detect
from agent.facts import METRIC_KIND, FactBook, residual_kind

TOP_ACTIONS = 3
MAX_WEEKS = 13
SCORE_NOTE = "uncalibrated score (robust z of the peer gap vs its own history) — not a probability the alert is real"
TREND_METRICS = sorted(METRIC_KIND)
COMPARE_METRICS = sorted(m for m, k in METRIC_KIND.items() if k in ("pct", "bps", "days", "ratio"))
LEVELS = ["segment", "market", "band", "portfolio"]
RANKED_ON = {"scenario_estimate": "midpoint of the scenario estimate", "measured": "measured $ at risk",
             "sensitivity": "$ per 100 bps (sensitivity only)"}


class ToolError(ValueError):
    pass


def _schema(name: str, description: str, properties: dict) -> dict:
    return {"name": name, "description": description,
            "input_schema": {"type": "object", "properties": properties, "required": sorted(properties),
                             "additionalProperties": False}}


WEEKS = {"type": "integer", "description": f"how many weeks to return (1 to {MAX_WEEKS}), ending at the brief's week"}
SCHEMAS = [
    _schema("get_alerts", "Active margin alerts for the brief's week: the top actions ranked by sample-scale $ at "
            "risk, each with its signal, impact (sample-scale $ and bps of contribution margin), action and owner; "
            "plus watch items and abstentions.", {}),
    _schema("query_metric", "Weekly values of one governed metric for one scope, ending at the brief's week.",
            {"metric": {"type": "string", "enum": TREND_METRICS}, "level": {"type": "string", "enum": LEVELS},
             "scope": {"type": "string", "description": "M01..M06, B1..B3, a segment like M02-B2-cash, or 'portfolio'"},
             "weeks": WEEKS}),
    _schema("compare_segments", "Peer comparison that separates seasonality from drift: the scope's value next to "
            "the volume-weighted median of peer segments in the same week (same other dimensions), the gap, and "
            "the latest uncalibrated drift score.",
            {"metric": {"type": "string", "enum": COMPARE_METRICS},
             "dimension": {"type": "string", "enum": ["market", "band"]},
             "scope": {"type": "string", "description": "a market (M01..M06) or band (B1..B3)"}, "weeks": WEEKS}),
    _schema("cohort_curve", "Cohort bleed curve: contribution margin of the first 10%..80% of a purchase cohort's "
            "homes to sell, as of the brief's week.",
            {"level": {"type": "string", "enum": ["market", "band", "portfolio"]}, "scope": {"type": "string"},
             "close_week_start": {"type": "integer", "description": "first purchase week of the cohort (>= 0)"},
             "close_week_end": {"type": "integer", "description": "last purchase week of the cohort (<= the brief's week)"}}),
]


class Toolbox:
    schemas = SCHEMAS

    def __init__(self, store: GovernedStore, as_of_week: int):
        self.store, self.as_of = store, as_of_week
        self.book = FactBook(store)
        self.facts = self.book.facts

    def run(self, name: str, args: dict) -> dict:
        handler = {"get_alerts": self.get_alerts, "query_metric": self.query_metric,
                   "compare_segments": self.compare_segments, "cohort_curve": self.cohort_curve}.get(name)
        if handler is None:
            raise ToolError(f"unknown tool {name!r}")
        try:
            return handler(**args)
        except ToolError:
            raise
        except (TypeError, ValueError) as exc:
            raise ToolError(str(exc)) from exc

    # --- get_alerts ---------------------------------------------------------------------------------------
    def get_alerts(self) -> dict:
        result = detect(self.store, self.as_of)
        ranked = rank_actions(result, self.store)
        alerts = {a.alert_id: a for a in result.alerts}
        return {
            "banner": SYNTHETIC_BANNER, "sample_scale_label": SAMPLE_SCALE_LABEL,
            "as_of_week": self.as_of, "week_start": self.store.week_start(self.as_of),
            "global_abstention": any(a.scope == "all" for a in result.abstentions),
            "actions": [self._action(r, alerts[r.alert_id]) for r in ranked[:TOP_ACTIONS]],
            "more_actions_not_shown": max(0, len(ranked) - TOP_ACTIONS) > 0,
            "watch": [{"scope": w.scope, "metric": w.metric, "note": w.note} for w in result.watch],
            "abstentions": sorted({(a.scope, a.metric or "all", _reason(a.reason)) for a in result.abstentions}),
        }

    def _action(self, ranked: RankedAction, alert) -> dict:
        signal = alert.signals[0]
        kind = residual_kind(METRIC_KIND.get(signal.metric, "ratio"))
        return {
            "rank": ranked.rank, "alert_id": alert.alert_id, "kind": alert.kind, "scope": alert.scope,
            "dimension": alert.dimension, "onset_week": alert.onset_week, "onset_week_start": self.store.week_start(alert.onset_week),
            "action": ranked.action, "owner": ranked.owner,
            "signal": {"metric": signal.metric, "direction": signal.direction, "score_note": SCORE_NOTE,
                       "score": self.book.cite(f"{alert.alert_id} score", signal.z, "score", signal.ref_ids,
                                               "uncalibrated drift score"),
                       "gap_vs_peers": self.book.cite(f"{alert.alert_id} gap vs peers", signal.residual, kind,
                                                      signal.ref_ids, "volume-weighted peer residual")},
            "supporting": [{"metric": s.metric, "direction": s.direction,
                            "score": self.book.cite(f"{alert.alert_id} supporting {s.metric} score", s.z, "score",
                                                    s.ref_ids, "uncalibrated drift score")} for s in alert.supporting],
            "impact": self._impact(alert, ranked.impact),
        }

    def _impact(self, alert, impact: Impact) -> dict:
        refs = impact.ref_ids
        cite = lambda name, kind: self.book.cite(f"{alert.alert_id} {name}", getattr(impact, name), kind, refs,  # noqa: E731
                                                 f"impact {impact.basis} {name}")
        out = {"basis": impact.basis, "status": impact.status, "label": impact.label,
               "ranked_on": RANKED_ON[impact.basis],
               "exposure_usd": cite("exposure_usd", "usd"), "usd_per_100bps": cite("usd_per_100bps", "usd")}
        if impact.basis != "sensitivity":
            for name in ("usd_low", "usd_mid", "usd_high"):
                out[name] = cite(name, "usd")
            for name in ("scope_bps_low", "scope_bps_mid", "scope_bps_high",
                         "portfolio_cm_bps_low", "portfolio_cm_bps_mid", "portfolio_cm_bps_high"):
                out[name] = cite(name, "bps")
        for fact_id in refs:
            label = getattr(self.store.get(fact_id), "label", "")
            if label.endswith(" excess_share"):
                out["excess_share"] = self.book.cite_existing(fact_id, "pct")
        if impact.basis == "scenario_estimate":
            low, _, high = ADVERSE_SELECTION_SHORTFALL
            out["shortfall_low"] = self.book.cite("planning shortfall low (user-given)", low, "pct", refs[:1], "assumption")
            out["shortfall_high"] = self.book.cite("planning shortfall high (user-given)", high, "pct", refs[:1], "assumption")
        return out

    # --- query_metric ---------------------------------------------------------------------------------------
    def query_metric(self, metric: str, level: str, scope: str, weeks: int) -> dict:
        if metric not in METRIC_KIND:
            raise ToolError(f"unknown metric {metric!r}")
        panel = self.store.panel(metric, level, self.as_of, WINDOW_WEEKS)
        rows = panel.values[(panel.values["scope"] == scope) & (panel.values["week"] > self.as_of - _weeks(weeks))]
        if rows.empty:
            raise ToolError(f"no data for scope {scope!r} at level {level!r}")
        kind = METRIC_KIND[metric]
        return {"metric": metric, "scope": scope, "window": f"trailing {WINDOW_WEEKS}-week sums",
                "rows": [{"week": int(r.week), "week_start": self.store.week_start(int(r.week)),
                          "value": self.book.cite(f"{metric} {scope} week {int(r.week)}", r.value, kind,
                                                  (panel.query_id,), f"governed metric {metric}")}
                         for r in rows.itertuples()]}

    # --- compare_segments -----------------------------------------------------------------------------------
    def compare_segments(self, metric: str, dimension: str, scope: str, weeks: int) -> dict:
        if metric not in COMPARE_METRICS:
            raise ToolError(f"metric {metric!r} cannot be peer-compared")
        segment = self.store.panel(metric, "segment", self.as_of, WINDOW_WEEKS, min_denominator=MIN_SEGMENT_SAMPLE)
        roll = rollup(peer_residuals(segment, dimension), dimension)
        own = roll[roll["scope"] == scope].set_index("week")
        if own.empty:
            raise ToolError(f"unknown {dimension} scope {scope!r}")
        scope_panel = self.store.panel(metric, dimension, self.as_of, WINDOW_WEEKS, min_denominator=MIN_SEGMENT_SAMPLE)
        values = scope_panel.values[scope_panel.values["scope"] == scope].set_index("week")["value"]
        refs = (segment.query_id, scope_panel.query_id)
        kind, gap_kind = METRIC_KIND[metric], residual_kind(METRIC_KIND[metric])
        rows = []
        for week in range(self.as_of - _weeks(weeks) + 1, self.as_of + 1):
            if week not in own.index:
                continue
            rows.append({"week": week, "week_start": self.store.week_start(week),
                         "scope_value": self.book.cite(f"{metric} {scope} week {week}", values.get(week), kind, refs, "scope value"),
                         "peer_median": self.book.cite(f"{metric} peers of {scope} week {week}", own.loc[week, "peer_level"],
                                                       kind, refs, "volume-weighted leave-one-out peer median"),
                         "gap": self.book.cite(f"{metric} {scope} gap vs peers week {week}", own.loc[week, "residual"],
                                               gap_kind, refs, "scope minus peers")})
        drift = score(own["residual"], self.as_of, metric, own["se"].fillna(0.0))
        latest = None
        if isinstance(drift, DriftScore):
            latest = {"score": self.book.cite(f"{metric} {scope} drift score week {self.as_of}", drift.z_latest,
                                              "score", refs, "uncalibrated drift score"),
                      "fired": drift.fired, "direction": drift.direction, "note": SCORE_NOTE}
        return {"metric": metric, "dimension": dimension, "scope": scope,
                "why": "peers share the same weeks, so seasonality moves them together; the gap is the drift",
                "rows": rows, "latest": latest}

    # --- cohort_curve ---------------------------------------------------------------------------------------
    def cohort_curve(self, level: str, scope: str, close_week_start: int, close_week_end: int) -> dict:
        panel = self.store.cohort_curve(level, scope, close_week_start, close_week_end, self.as_of)
        frame = panel.values
        refs = (panel.query_id,)
        return {"scope": scope, "close_week_start": close_week_start, "close_week_end": close_week_end,
                "cohort_homes": self.book.cite(f"cohort {scope} {close_week_start}-{close_week_end} homes",
                                               float(frame["n_homes"].iloc[0]), "count", refs, "cohort size"),
                "points": [{"sold_share": self.book.cite(f"sold share {r.sold_share}", float(r.sold_share), "pct",
                                                         refs, "checkpoint"),
                            "cm_pct": self.book.cite(f"cohort {scope} {close_week_start}-{close_week_end} cm at "
                                                     f"{r.sold_share}", r.cm_pct, "pct", refs,
                                                     "contribution margin of homes sold so far")}
                           for r in frame.itertuples()]}


def _weeks(weeks: int) -> int:
    if not isinstance(weeks, int) or not 1 <= weeks <= MAX_WEEKS:
        raise ToolError(f"weeks must be an integer in 1..{MAX_WEEKS}")
    return weeks


def _reason(reason: str) -> str:
    return "not enough history yet" if "history" in reason else "too little volume this week"
