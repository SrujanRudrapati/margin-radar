"""Agent tools on the seed-42 injected run: every number ships with a citation ID."""
import json

import pytest

from agent.facts import fmt, parse_number
from agent.tools import Toolbox, ToolError
from detector.governed import GovernedStore

AS_OF = 40


@pytest.fixture(scope="module")
def toolbox(built_runs):
    store = GovernedStore(str(built_runs["injected"]), "injected")
    yield Toolbox(store, AS_OF)
    store.close()


def _cites(obj):
    """Yield every {"value": ..., "ref": ...} citation object in a tool result."""
    if isinstance(obj, dict):
        if set(obj) == {"value", "ref"}:
            yield obj
        for v in obj.values():
            yield from _cites(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _cites(v)


def _bare_numbers(obj, path=""):
    """Numbers that are not inside a citation object (weeks and counts of rows are allowed context)."""
    if isinstance(obj, dict):
        if set(obj) == {"value", "ref"}:
            return []
        out = []
        for k, v in obj.items():
            out += _bare_numbers(v, f"{path}.{k}")
        return out
    if isinstance(obj, list):
        return [x for i, v in enumerate(obj) for x in _bare_numbers(v, f"{path}[{i}]")]
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return [path]
    return []


ALLOWED_BARE = ("week", "rank", "onset_week", "close_week_start", "close_week_end", "as_of_week")


def test_fmt_and_parse_round_trip():
    assert fmt(1_406_374, "usd") == "$1.4M" and fmt(328_226, "usd") == "$328K"
    assert fmt(0.4523, "pct") == "45.2%" and fmt(0.0981, "pct_points") == "+9.8 pts"
    assert fmt(28.4, "bps") == "28 bps" and fmt(3.37, "score") == "3.4"
    assert parse_number("$1.4M") == pytest.approx(1.4e6) and parse_number("45.2%") == pytest.approx(0.452)
    assert parse_number("+9.8 pts") == pytest.approx(0.098) and parse_number("28 bps") == pytest.approx(28)


def test_schemas_have_no_run_or_as_of_parameter(toolbox):
    names = {t["name"] for t in toolbox.schemas}
    assert names == {"get_alerts", "query_metric", "compare_segments", "cohort_curve"}
    for tool in toolbox.schemas:
        props = tool["input_schema"].get("properties", {})
        assert not {"run_id", "run", "as_of", "as_of_week", "db"} & set(props)
        assert tool["input_schema"]["additionalProperties"] is False


@pytest.mark.parametrize("name,args", [
    ("get_alerts", {}),
    ("query_metric", {"metric": "contract_rate", "level": "band", "scope": "B2", "weeks": 6}),
    ("compare_segments", {"metric": "contract_rate", "dimension": "band", "scope": "B2", "weeks": 6}),
    ("cohort_curve", {"level": "band", "scope": "B2", "close_week_start": 20, "close_week_end": 23}),
])
def test_every_number_is_cited(toolbox, name, args):
    result = toolbox.run(name, args)
    json.dumps(result)  # serialisable
    cites = list(_cites(result))
    assert cites, name
    for c in cites:
        assert c["ref"].startswith("q:D") and c["ref"][2:] in toolbox.facts
    bare = [p for p in _bare_numbers(result) if not p.split(".")[-1].split("[")[0] in ALLOWED_BARE]
    assert bare == [], bare


def test_get_alerts_has_ranked_actions_with_range(toolbox):
    result = toolbox.run("get_alerts", {})
    assert result["as_of_week"] == AS_OF and result["banner"].startswith("Synthetic data")
    kinds = {(a["kind"], a["scope"]) for a in result["actions"]}
    assert ("adverse_selection", "B2") in kinds
    b2 = next(a for a in result["actions"] if a["scope"] == "B2")
    assert b2["impact"]["basis"] == "scenario_estimate" and b2["impact"]["status"] == "unconfirmed until resales"
    assert {"usd_low", "usd_mid", "usd_high", "portfolio_cm_bps_mid", "excess_share"} <= set(b2["impact"])
    assert "uncalibrated" in b2["signal"]["score_note"]


def test_bad_arguments_raise_tool_error(toolbox):
    with pytest.raises(ToolError):
        toolbox.run("query_metric", {"metric": "drop table", "level": "band", "scope": "B2", "weeks": 4})
    with pytest.raises(ToolError):
        toolbox.run("compare_segments", {"metric": "contract_rate", "dimension": "band", "scope": "B9", "weeks": 4})
    with pytest.raises(ToolError):
        toolbox.run("nope", {})
