"""Manual tool-use loop (DECISIONS D3): every turn is one cache-keyed LLM.create call. Synthetic data — not Opendoor data."""
import json
from pathlib import Path

from agent.llm import with_prompt_caching
from agent.tools import ToolError

SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "brief_system.md"
MAX_TOKENS = 4096
# Content-block keys to echo back per type (thinking blocks must go back unchanged on the same model).
_KEEP = {"text": ("type", "text"), "tool_use": ("type", "id", "name", "input"),
         "thinking": ("type", "thinking", "signature"), "redacted_thinking": ("type", "data")}


class AgentDidNotFinish(RuntimeError):
    pass


def system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text()


def user_prompt(as_of_week: int, week_start: str, feedback: str | None = None) -> str:
    text = (f"Write the weekly margin brief for week {as_of_week} (the week starting {week_start}). "
            "Start with get_alerts, then gather the peer comparison for each action you report.")
    if feedback:
        text += ("\n\nA previous draft failed the grounding check. Fix every problem below; copy numbers exactly "
                 f"as the tools display them, each followed by its [q:ID]:\n{feedback}")
    return text


def run_agent(llm, toolbox, as_of_week: int, week_start: str, max_turns: int = 8, feedback: str | None = None) -> str:
    system, tools = with_prompt_caching([{"type": "text", "text": system_prompt()}],
                                        [{**t, "strict": True} for t in toolbox.schemas])
    messages = [{"role": "user", "content": user_prompt(as_of_week, week_start, feedback)}]
    for _ in range(max_turns):
        response = llm.create(system=system, messages=messages, tools=tools, max_tokens=MAX_TOKENS)
        stop = response.get("stop_reason")
        blocks = response.get("content") or []
        if stop == "end_turn":
            return "\n".join(b["text"] for b in blocks if b.get("type") == "text").strip()
        if stop != "tool_use":
            raise AgentDidNotFinish(f"model stopped with stop_reason={stop!r}")
        messages.append({"role": "assistant", "content": [_echo(b) for b in blocks if b.get("type") in _KEEP]})
        messages.append({"role": "user", "content": [_run(toolbox, b) for b in blocks if b.get("type") == "tool_use"]})
    raise AgentDidNotFinish(f"no final brief after {max_turns} turns")


def _echo(block: dict) -> dict:
    return {k: block[k] for k in _KEEP[block["type"]] if k in block}


def _run(toolbox, block: dict) -> dict:
    try:
        content, is_error = json.dumps(toolbox.run(block["name"], block.get("input") or {}), default=str), False
    except ToolError as exc:
        content, is_error = f"Error: {exc}", True
    result = {"type": "tool_result", "tool_use_id": block["id"], "content": content}
    if is_error:
        result["is_error"] = True
    return result
