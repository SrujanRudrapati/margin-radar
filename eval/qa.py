"""Semantic-layer accuracy and abstention (docs/SPEC.md Phase 5).

20 natural-language questions with gold answers from the governed semantic layer, answered twice by the model:
via the governed `query_metric` tool, and via read-only raw SQL against the DuckDB file. Plus 5 unanswerable
questions where the right behaviour is to abstain. Conversations advance in lockstep so each turn can go out as one
Message Batch. Synthetic data — not Opendoor data.
"""
import json
import re
import shutil
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

import duckdb

from agent.llm import with_prompt_caching
from detector.governed import GovernedStore

RUN_ID = "injected"
MAX_TURNS = 5
SQL_TIMEOUT_S = 10
MAX_ROWS = 200
REL_TOL = 0.005

_Q = [  # (id, metric, level, scope, week, window, wording)
    ("q01", "contract_rate", "band", "B2", 40, 4, "the contract rate (contracts signed / offers made) for price band B2"),
    ("q02", "first_offer_rate", "market", "M02", 45, 4, "the first-offer rate (first buyer offers / listing-weeks awaiting an offer) for market M02"),
    ("q03", "reno_overrun_pct", "market", "M05", 44, 4, "the renovation overrun (actual / estimated renovation cost - 1) for market M05"),
    ("q04", "contribution_margin_pct", "portfolio", "portfolio", 26, 13, "the contribution margin (sold-cohort contribution margin / resale revenue) for the whole portfolio"),
    ("q05", "offers", "portfolio", "portfolio", 20, 1, "the number of offers made across the whole portfolio"),
    ("q06", "avg_spread_pct", "band", "B2", 40, 4, "the average offer spread for price band B2"),
    ("q07", "closes", "market", "M03", 50, 4, "the number of home purchases closed in market M03"),
    ("q08", "resale_usd", "portfolio", "portfolio", 60, 13, "the total resale revenue in dollars for the whole portfolio"),
    ("q09", "price_cut_rate", "market", "M02", 50, 4, "the price-cut rate (price cuts / listing-weeks awaiting an offer) for market M02"),
    ("q10", "avg_days_to_first_offer", "market", "M04", 52, 4, "the average days from listing to first buyer offer for market M04"),
    ("q11", "unsold_inventory_usd", "portfolio", "portfolio", 40, 1, "the unsold inventory value in dollars (cash paid for homes bought and not yet resold) for the whole portfolio at the end of the week"),
    ("q12", "fall_through_rate", "portfolio", "portfolio", 35, 13, "the fall-through rate (contracts cancelled by the seller / contracts signed) for the whole portfolio"),
    ("q13", "contract_rate", "segment", "M02-B2-cash", 40, 4, "the contract rate for segment M02-B2-cash (market M02, band B2, cash product)"),
    ("q14", "company_decline_rate", "portfolio", "portfolio", 30, 13, "the company-decline rate (contracts we declined after inspection / contracts signed) for the whole portfolio"),
    ("q15", "holding_cost_bps_per_day", "portfolio", "portfolio", 52, 13, "the holding cost in basis points of resale price per day held, for the whole portfolio"),
    ("q16", "resale_vs_model_bps", "band", "B2", 60, 4, "the realized resale price versus model valuation, in basis points, for price band B2"),
    ("q17", "acquisition_usd", "market", "M01", 30, 4, "the dollar value of home purchases closed in market M01"),
    ("q18", "showing_rate_per_week", "market", "M02", 55, 4, "the number of showings per listing-week before the first buyer offer, for market M02"),
    ("q19", "contribution_margin_pct", "band", "B3", 39, 13, "the contribution margin (sold-cohort contribution margin / resale revenue) for price band B3"),
    ("q20", "offers", "band", "B1", 10, 4, "the number of offers made in price band B1"),
]


def _window_phrase(week: int, window: int) -> str:
    return f"in week {week}" if window == 1 else f"over the {window} weeks ending week {week} (weeks {week - window + 1} to {week})"


QUESTIONS = [{"id": i, "metric": m, "level": lvl, "scope": sc, "week": w, "window_weeks": win,
              "text": f"What was {wording} {_window_phrase(w, win)}? Give rates as fractions, money in dollars, "
                      "basis points as basis points."}
             for i, m, lvl, sc, w, win, wording in _Q]
UNANSWERABLE = [
    {"id": "u01", "text": "What was Opendoor's actual contribution margin in Q3 2025?"},
    {"id": "u02", "text": "What was the contract rate for market M09 in week 40?"},
    {"id": "u03", "text": "What will the contract rate for price band B2 be in week 90?"},
    {"id": "u04", "text": "What was the contract rate in Phoenix in week 40?"},
    {"id": "u05", "text": "How many homes were bought in 2024?"},
]

ANSWER = {"name": "answer", "description": "Submit the final numeric answer (rates as fractions, money in dollars, "
          "basis points as basis points). Call exactly once.",
          "input_schema": {"type": "object", "properties": {"value": {"type": "number"}}, "required": ["value"],
                           "additionalProperties": False}}
ABSTAIN = {"name": "abstain", "description": "Use when the question cannot be answered from this data (unknown "
           "scope, outside the data's weeks, real-company data, or anything not measured here).",
           "input_schema": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"],
                            "additionalProperties": False}}
QUERY_METRIC = {"name": "query_metric", "description": "Governed semantic-layer metric for one scope and week, "
                "summed over a trailing window of weeks.",
                "input_schema": {"type": "object", "additionalProperties": False,
                                 "required": ["metric", "level", "scope", "week", "window_weeks"],
                                 "properties": {"metric": {"type": "string"},
                                                "level": {"type": "string", "enum": ["segment", "market", "band", "portfolio"]},
                                                "scope": {"type": "string"}, "week": {"type": "integer"},
                                                "window_weeks": {"type": "integer", "description": "1, 4 or 13"}}}}
RUN_SQL = {"name": "run_sql", "description": f"Run one read-only SELECT against the DuckDB database (max {MAX_ROWS} rows).",
           "input_schema": {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"],
                            "additionalProperties": False}}

SYSTEM_COMMON = ("You answer questions about a synthetic iBuyer portfolio (not Opendoor data). Weeks are numbered "
                 "from 0 (week 0 starts 2025-01-06); the data covers weeks 0 to 77. Markets are M01..M06, price bands "
                 "B1..B3, products cash and CNML. Be precise. Finish by calling `answer` with one number, or `abstain` "
                 "if the question cannot be answered from this data. Do not guess.")
SYSTEM = {
    "semantic": SYSTEM_COMMON + " Use `query_metric` (the governed semantic layer) to get values. Metrics: "
                "{metrics}. Answer with the `raw_value` it returns.",
    "raw_sql": SYSTEM_COMMON + " Use `run_sql` to compute the answer yourself from the tables below. Window sums: "
               "add numerators and denominators over the window's weeks, then divide.\n{schema}",
}
_FORBIDDEN = re.compile(r"\b(attach|detach|copy|install|load|pragma|export|import|create|insert|update|delete|drop|alter|"
                        r"call|set|read_\w+|glob|httpfs)\b", re.IGNORECASE)


_ORDER_BY = re.compile(r"\border\s+by\b", re.IGNORECASE)
_WINDOW = re.compile(r"\bover\s*\([^)]*\)", re.IGNORECASE)  # ORDER BY inside OVER (...) orders a window, not rows


def sql_guard(sql: str) -> str:
    text = sql.strip().rstrip(";").strip()
    if ";" in text:
        raise ValueError("one statement only")
    if not re.match(r"^(select|with)\b", text, re.IGNORECASE):
        raise ValueError("only SELECT or WITH queries are allowed")
    if _FORBIDDEN.search(text):
        raise ValueError("statement uses a forbidden keyword or table function")
    return text


@contextmanager
def open_sql(db: str | Path):
    """Read-only DuckDB connection for model-written SQL, with external access off: no replacement scans of
    files ('path.json'), no read_*/sniff_csv, no ATTACH. It opens a private temp copy of the database, because
    DuckDB will not open one file twice in a process with different settings. One thread keeps the row order of
    unordered queries stable, so replayed conversations see the same tool results."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / Path(db).name
        shutil.copy(db, copy)
        con = duckdb.connect(str(copy), read_only=True, config={"enable_external_access": False, "threads": 1})
        try:
            yield con
        finally:
            con.close()


def grade(answer: float | None, gold: float | None) -> bool:
    if answer is None or gold is None:
        return False
    if gold == 0:
        return abs(answer) < 1e-9
    return abs(answer - gold) / abs(gold) <= REL_TOL


class Conversation:
    def __init__(self, item: dict, answerable: bool):
        self.item, self.answerable = item, answerable
        self.messages = [{"role": "user", "content": item["text"]}]
        self.done, self.answer, self.abstained, self.note = False, None, False, ""

    def step(self, response: dict, run_tool) -> None:
        blocks = response.get("content") or []
        if response.get("stop_reason") != "tool_use":
            self.done, self.note = True, f"stopped: {response.get('stop_reason')}"
            return
        keep = {"text": ("type", "text"), "tool_use": ("type", "id", "name", "input"),
                "thinking": ("type", "thinking", "signature"), "redacted_thinking": ("type", "data")}
        self.messages.append({"role": "assistant", "content": [{k: b[k] for k in keep[b["type"]] if k in b}
                                                               for b in blocks if b.get("type") in keep]})
        results = []
        for b in blocks:
            if b.get("type") != "tool_use":
                continue
            if b["name"] == "answer":
                self.answer, self.done = float(b["input"]["value"]), True
                content, err = "recorded", False
            elif b["name"] == "abstain":
                self.abstained, self.done = True, True
                content, err = "recorded", False
            else:
                try:
                    content, err = json.dumps(run_tool(b["name"], b["input"]), default=str), False
                except (ValueError, duckdb.Error, KeyError, TypeError) as exc:
                    content, err = f"Error: {exc}", True
            result = {"type": "tool_result", "tool_use_id": b["id"], "content": content}
            if err:
                result["is_error"] = True
            results.append(result)
        self.messages.append({"role": "user", "content": results})


def run_qa(llm, db: str | Path, mode: str, questions=QUESTIONS, unanswerable=UNANSWERABLE, max_turns: int = MAX_TURNS) -> dict:
    with GovernedStore(str(db), RUN_ID) as store, open_sql(db) as con:
        gold = {q["id"]: _gold(store, q) for q in questions}
        system_text = SYSTEM[mode].format(metrics=", ".join(store.metrics()), schema=_schema(con))
        tools = [QUERY_METRIC if mode == "semantic" else RUN_SQL, ANSWER, ABSTAIN]
        system, tools = with_prompt_caching([{"type": "text", "text": system_text}], [{**t, "strict": True} for t in tools])
        run_tool = (lambda name, args: _query_metric(store, **args)) if mode == "semantic" else \
            (lambda name, args: _run_sql(con, **args))
        convs = [Conversation(q, True) for q in questions] + [Conversation(u, False) for u in unanswerable]
        for _ in range(max_turns):
            active = [c for c in convs if not c.done]
            if not active:
                break
            responses = llm.create_many([{"system": system, "messages": c.messages, "tools": tools, "max_tokens": 4096}
                                         for c in active])
            for c, response in zip(active, responses):
                c.step(response, run_tool)
    rows = [{"id": c.item["id"], "answerable": c.answerable, "gold": gold.get(c.item["id"]), "answer": c.answer,
             "abstained": c.abstained, "correct": c.answerable and grade(c.answer, gold.get(c.item["id"])),
             "note": c.note} for c in convs]
    answerable = [r for r in rows if r["answerable"]]
    unans = [r for r in rows if not r["answerable"]]
    return {"mode": mode, "rows": rows, "answered": sum(r["answer"] is not None for r in answerable),
            "accuracy": sum(r["correct"] for r in answerable) / len(answerable) if answerable else None,
            "false_abstentions": sum(r["abstained"] for r in answerable),
            "abstention_rate": sum(r["abstained"] for r in unans) / len(unans) if unans else None}


def _gold(store: GovernedStore, q: dict) -> float | None:
    panel = store.panel(q["metric"], q["level"], q["week"], q["window_weeks"])
    row = panel.values[(panel.values["scope"] == q["scope"]) & (panel.values["week"] == q["week"])]
    value = row["value"].iloc[0] if len(row) else None
    return None if value is None else float(value)


def _query_metric(store: GovernedStore, metric: str, level: str, scope: str, week: int, window_weeks: int) -> dict:
    if int(window_weeks) not in (1, 4, 13):
        raise ValueError("window_weeks must be 1, 4 or 13")
    panel = store.panel(metric, level, int(week), int(window_weeks))
    row = panel.values[(panel.values["scope"] == scope) & (panel.values["week"] == int(week))]
    if row.empty:
        raise ValueError(f"no data for {level} {scope!r}")
    value = row["value"].iloc[0]
    return {"metric": metric, "level": level, "scope": scope, "week": int(week), "window_weeks": int(window_weeks),
            "raw_value": None if value is None else _canonical(float(value)), "query_id": panel.query_id}


def _run_sql(con, sql: str) -> dict:
    timer = threading.Timer(SQL_TIMEOUT_S, con.interrupt)  # a runaway cross join must not stall the batch
    timer.start()
    try:
        query = sql_guard(sql)
        own_order = _ORDER_BY.search(_WINDOW.sub("", query))
        order = "" if own_order else " order by all"  # stable rows (and LIMIT) when the model gave no order
        rows = con.execute(f"select * from ({query}) as q{order} limit {MAX_ROWS}").fetchall()
    finally:
        timer.cancel()
    columns = [d[0] for d in con.description]
    return {"columns": columns, "rows": [[_canonical(v) for v in r] for r in rows]}


def _canonical(value):
    """Floats to 10 significant digits: sums over a rebuilt database differ only in their last bits, and the tool
    output is part of the next turn's replay cache key."""
    return float(f"{value:.10g}") if isinstance(value, float) else value


def _schema(con) -> str:
    lines = []
    for schema, table in (("main", "mart_segment_week"), ("raw", "homes"), ("raw", "price_cuts")):
        cols = [f"{c} {t}" for c, t, *_ in con.execute(f"describe {schema}.{table}").fetchall()]
        lines.append(f"{schema}.{table}({', '.join(cols)})")
    return "Tables:\n" + "\n".join(lines)
