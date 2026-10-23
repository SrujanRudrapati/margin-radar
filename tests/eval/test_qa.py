import json

import pytest

from eval.qa import QUESTIONS, UNANSWERABLE, Conversation, grade, run_qa, sql_guard


def test_question_set_sizes():
    assert len(QUESTIONS) == 20 and len(UNANSWERABLE) == 5
    assert len({q["id"] for q in QUESTIONS + UNANSWERABLE}) == 25


@pytest.mark.parametrize("answer,gold,ok", [
    (0.4658, 0.46581, True), (46.58, 0.46581, False), (1_406_000, 1_406_374, True), (1_300_000, 1_406_374, False),
    (0.0, 0.0, True), (None, 0.3, False),
])
def test_grade(answer, gold, ok):
    assert grade(answer, gold) is ok


@pytest.mark.parametrize("sql", [
    "drop table x", "select 1; select 2", "attach 'x.duckdb'", "select * from read_parquet('x')",
    "copy t to 'x.csv'", "pragma version", "install httpfs",
])
def test_sql_guard_rejects(sql):
    with pytest.raises(ValueError):
        sql_guard(sql)


def test_sql_guard_allows_select():
    assert sql_guard("with a as (select 1 as x) select x from a").startswith("with")


class ScriptedMany:
    """Answers every question by calling the tool once, then answering with whatever value the tool returned."""

    def __init__(self):
        self.rounds = 0

    def create_many(self, requests):
        self.rounds += 1
        out = []
        for r in requests:
            last = r["messages"][-1]["content"]
            if isinstance(last, str):
                if "Opendoor" in last:
                    out.append({"stop_reason": "tool_use", "usage": {}, "content": [
                        {"type": "tool_use", "id": "a1", "name": "abstain", "input": {"reason": "not in data"}}]})
                else:
                    q = next(q for q in QUESTIONS if q["text"] == last)
                    out.append({"stop_reason": "tool_use", "usage": {}, "content": [
                        {"type": "tool_use", "id": "t1", "name": "query_metric",
                         "input": {k: q[k] for k in ("metric", "level", "scope", "week", "window_weeks")}}]})
            else:
                value = json.loads(last[0]["content"])["raw_value"]
                out.append({"stop_reason": "tool_use", "usage": {}, "content": [
                    {"type": "tool_use", "id": "t2", "name": "answer", "input": {"value": value}}]})
        return out


def test_run_qa_semantic_with_scripted_model(built_runs):
    result = run_qa(ScriptedMany(), built_runs["injected"], mode="semantic",
                    questions=QUESTIONS[:3], unanswerable=[u for u in UNANSWERABLE if "Opendoor" in u["text"]][:1])
    assert result["accuracy"] == 1.0 and result["answered"] == 3
    assert result["abstention_rate"] == 1.0
    assert all(r["gold"] is not None for r in result["rows"] if r["answerable"])


def test_raw_sql_cannot_read_files(built_runs, tmp_path):
    from eval.qa import open_sql
    secret = tmp_path / "secret.env"
    secret.write_text("MARGIN_RADAR_API_KEY=sk-fake-123\n")
    with open_sql(built_runs["injected"]) as con:
        assert con.execute("select count(*) from raw.homes").fetchone()[0] > 0
        for sql in (f"select * from '{secret}'", f"select * from sniff_csv('{secret}')",
                    f"select * from read_csv('{secret}')"):
            with pytest.raises(Exception):
                con.execute(sql).fetchall()


def test_raw_sql_is_single_threaded_so_unordered_results_replay(built_runs):
    # an unordered GROUP BY on a multi-threaded connection returns rows in varying order, which changes the next
    # turn's cache key and breaks replay; one thread makes the same query return the same order every run
    from eval.qa import open_sql
    with open_sql(built_runs["injected"]) as con:
        assert con.execute("select current_setting('threads')").fetchone()[0] == 1


def test_raw_sql_results_do_not_depend_on_physical_row_order():
    # dbt rebuilds change physical row order, so unordered results and float sums differ in their last bits;
    # the tool output feeds the next turn's cache key, so it must be canonical for replay to work after a rebuild
    import duckdb
    from eval.qa import _run_sql
    con = duckdb.connect()
    unordered = _run_sql(con, "select * from (values ('b', 2), ('a', 1), ('c', 3)) t(k, v)")
    assert unordered["rows"] == [["a", 1], ["b", 2], ["c", 3]]
    ordered = _run_sql(con, "select * from (values ('b', 2), ('a', 1)) t(k, v) order by v desc")
    assert ordered["rows"] == [["b", 2], ["a", 1]]  # the model's own ORDER BY is kept
    windowed = _run_sql(con, "select k, sum(v) over (order by v desc) as s from (values ('b', 2), ('a', 1)) t(k, v)")
    assert windowed["rows"] == [["a", 3], ["b", 2]]  # an ORDER BY inside OVER (...) does not order the output
    floats = _run_sql(con, "select 0.010813380726812483::double as x, 0.01081338072681226::double as y")
    assert floats["rows"][0][0] == floats["rows"][0][1]


def test_semantic_tool_value_is_canonical(built_runs):
    # the governed metric value is a float sum whose last bits change with each dbt rebuild; see D25
    from detector.governed import GovernedStore
    from eval.qa import _query_metric
    with GovernedStore(str(built_runs["injected"]), "injected") as store:
        out = _query_metric(store, "resale_usd", "portfolio", "portfolio", 60, 13)
    assert out["raw_value"] == float(f"{out['raw_value']:.10g}")
    assert len(repr(out["raw_value"]).replace(".", "").lstrip("0")) <= 11
