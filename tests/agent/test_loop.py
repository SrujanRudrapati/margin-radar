"""Tool loop with a scripted fake LLM (no network)."""
import pytest

from agent.loop import AgentDidNotFinish, run_agent


class ScriptedLLM:
    def __init__(self, responses):
        self.responses, self.requests = list(responses), []

    def create(self, *, system, messages, tools, max_tokens):
        self.requests.append({"system": system, "messages": [dict(m) for m in messages], "tools": tools})
        return self.responses.pop(0)


class FakeToolbox:
    schemas = [{"name": "get_alerts", "description": "d",
                "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}}]

    def __init__(self):
        self.calls = []

    def run(self, name, args):
        self.calls.append((name, args))
        return {"as_of_week": 40, "actions": []}


def tool_use(name="get_alerts", args=None, id_="tu_1"):
    return {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": id_, "name": name, "input": args or {}}],
            "usage": {}}


def final(text="# Brief"):
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}], "usage": {}}


def test_loop_calls_tools_then_returns_text():
    llm, tb = ScriptedLLM([tool_use(), final("body")]), FakeToolbox()
    text = run_agent(llm, tb, as_of_week=40, week_start="2025-10-13")
    assert text == "body" and tb.calls == [("get_alerts", {})]
    second = llm.requests[1]["messages"]
    assert second[-1]["content"][0]["type"] == "tool_result" and second[-1]["content"][0]["tool_use_id"] == "tu_1"
    assert llm.requests[0]["system"][-1]["cache_control"] == {"type": "ephemeral"}
    assert llm.requests[0]["tools"][-1]["cache_control"] == {"type": "ephemeral"}


def test_tool_error_is_returned_not_raised():
    class Boom(FakeToolbox):
        def run(self, name, args):
            from agent.tools import ToolError
            raise ToolError("bad scope")
    llm = ScriptedLLM([tool_use(), final("ok")])
    assert run_agent(llm, Boom(), as_of_week=40, week_start="2025-10-13") == "ok"
    result = llm.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True and "bad scope" in result["content"]


def test_max_turns_raises():
    llm = ScriptedLLM([tool_use(id_=f"t{i}") for i in range(3)])
    with pytest.raises(AgentDidNotFinish):
        run_agent(llm, FakeToolbox(), as_of_week=40, week_start="2025-10-13", max_turns=3)


def test_refusal_raises():
    llm = ScriptedLLM([{"stop_reason": "refusal", "content": [], "usage": {}}])
    with pytest.raises(AgentDidNotFinish):
        run_agent(llm, FakeToolbox(), as_of_week=40, week_start="2025-10-13")
