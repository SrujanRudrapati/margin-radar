"""LLM client: record/replay cache, budget cap, token log, key handling. No test touches the network."""
import json
import os
from pathlib import Path

import pytest

from agent.config import model_for
from agent.llm import LLM, BudgetExceeded, MissingKey, ReplayMiss, cache_key, with_prompt_caching
from agent.pricing import estimate_cost

SYSTEM = [{"type": "text", "text": "You are a test."}]
TOOLS = [{"name": "t", "description": "d", "input_schema": {"type": "object", "properties": {}}}]


def msgs(text="hi"):
    return [{"role": "user", "content": text}]


class FakeClient:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return {"id": "msg_1", "type": "message", "role": "assistant", "model": kwargs["model"],
                "content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn",
                "usage": {"input_tokens": 100, "output_tokens": 20, "cache_creation_input_tokens": 0,
                          "cache_read_input_tokens": 0}}


@pytest.fixture
def fake():
    return FakeClient()


def make(tmp_path, fake, **kw):
    return LLM(model="claude-haiku-5-5", purpose="dev", cache_dir=tmp_path / "cache", token_log=tmp_path / "log.jsonl",
               client_factory=lambda: fake, **kw)


def live(monkeypatch):
    monkeypatch.setenv("REPLAY", "0")
    monkeypatch.setenv("MARGIN_RADAR_API_KEY", "sk-test-SENTINEL-not-a-real-key")


def test_model_for_defaults(monkeypatch):
    monkeypatch.delenv("CLAUDE_MODEL_DEV", raising=False)
    monkeypatch.delenv("CLAUDE_MODEL_FINAL", raising=False)
    assert model_for("dev") == "claude-haiku-5-5"
    assert model_for("final") == "claude-sonnet-5-5"


def test_cache_hit_no_client_call(tmp_path, fake, monkeypatch):
    live(monkeypatch)
    llm = make(tmp_path, fake)
    first = llm.create(system=SYSTEM, messages=msgs(), tools=TOOLS, max_tokens=100)
    second = make(tmp_path, fake).create(system=SYSTEM, messages=msgs(), tools=TOOLS, max_tokens=100)
    assert len(fake.calls) == 1 and first == second
    lines = [json.loads(l) for l in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert [l["replay"] for l in lines] == [False, True]
    assert lines[1]["est_cost_usd"] == 0


def test_replay_miss_raises_with_hint(tmp_path, fake, monkeypatch):
    monkeypatch.setenv("REPLAY", "1")
    with pytest.raises(ReplayMiss) as err:
        make(tmp_path, fake).create(system=SYSTEM, messages=msgs("new"), tools=TOOLS, max_tokens=100)
    assert "REPLAY=0" in str(err.value) and len(str(err.value).split()) > 3
    assert fake.calls == []


def test_budget_exceeded_before_call(tmp_path, fake, monkeypatch):
    live(monkeypatch)
    llm = make(tmp_path, fake, max_calls=2)
    llm.create(system=SYSTEM, messages=msgs("a"), tools=TOOLS, max_tokens=10)
    llm.create(system=SYSTEM, messages=msgs("b"), tools=TOOLS, max_tokens=10)
    with pytest.raises(BudgetExceeded):
        llm.create(system=SYSTEM, messages=msgs("c"), tools=TOOLS, max_tokens=10)
    assert len(fake.calls) == 2


def test_missing_key_message_has_no_value(tmp_path, monkeypatch):
    monkeypatch.setenv("REPLAY", "0")
    monkeypatch.delenv("MARGIN_RADAR_API_KEY", raising=False)
    monkeypatch.setattr("agent.llm.load_dotenv", lambda *a, **k: False)
    llm = LLM(model="claude-haiku-5-5", purpose="dev", cache_dir=tmp_path / "c", token_log=tmp_path / "l.jsonl")
    with pytest.raises(MissingKey) as err:
        llm.create(system=SYSTEM, messages=msgs(), tools=TOOLS, max_tokens=10)
    assert "MARGIN_RADAR_API_KEY" in str(err.value)


def test_key_never_in_logs_or_cache(tmp_path, fake, monkeypatch):
    live(monkeypatch)
    make(tmp_path, fake).create(system=SYSTEM, messages=msgs(), tools=TOOLS, max_tokens=10)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert "SENTINEL" not in path.read_text()


def test_cache_key_order_insensitive_dicts():
    a = cache_key("m", SYSTEM, [{"role": "user", "content": "x"}], [{"name": "t", "description": "d"}])
    b = cache_key("m", SYSTEM, [{"content": "x", "role": "user"}], [{"description": "d", "name": "t"}])
    assert a == b and a != cache_key("m2", SYSTEM, msgs("x"), TOOLS)


def test_prompt_caching_markers():
    system, tools = with_prompt_caching(SYSTEM, TOOLS + [{"name": "u", "description": "e", "input_schema": {}}])
    assert system[-1]["cache_control"] == {"type": "ephemeral"}
    assert tools[-1]["cache_control"] == {"type": "ephemeral"} and "cache_control" not in tools[0]
    assert "cache_control" not in SYSTEM[-1]  # input not mutated


def test_token_log_fields(tmp_path, fake, monkeypatch):
    live(monkeypatch)
    make(tmp_path, fake, run_tag="t1").create(system=SYSTEM, messages=msgs(), tools=TOOLS, max_tokens=10)
    line = json.loads((tmp_path / "log.jsonl").read_text().splitlines()[0])
    assert {"ts", "model", "purpose", "run_tag", "input_tokens", "output_tokens", "cache_creation_input_tokens",
            "cache_read_input_tokens", "est_cost_usd", "replay"} <= set(line)
    assert line["est_cost_usd"] == pytest.approx(100 * 0.10 / 1e6 + 20 * 0.50 / 1e6)


def test_unknown_model_cost_none():
    assert estimate_cost("claude-unknown", {"input_tokens": 10, "output_tokens": 1}) is None


def test_no_network_in_pytest(tmp_path):
    # conftest forces REPLAY=1 and removes the key: an uncached request must raise, never call out.
    assert os.environ.get("REPLAY") == "1" and "MARGIN_RADAR_API_KEY" not in os.environ
    llm = LLM(model="claude-haiku-5-5", purpose="dev", cache_dir=tmp_path / "c", token_log=tmp_path / "l.jsonl")
    with pytest.raises(ReplayMiss):
        llm.create(system=SYSTEM, messages=msgs("uncached"), tools=TOOLS, max_tokens=10)


class FakeBatchClient(FakeClient):
    def __init__(self, fail_index=None):
        super().__init__()
        self.batches, self.fail_index = [], fail_index

    def run_batch(self, params_list, timeout_s):
        self.batches.append(len(params_list))
        out = []
        for i, p in enumerate(params_list):
            out.append(None if i == self.fail_index else
                       {"id": f"b{i}", "type": "message", "role": "assistant", "model": p["model"],
                        "content": [{"type": "text", "text": f"batch {i}"}], "stop_reason": "end_turn",
                        "usage": {"input_tokens": 100, "output_tokens": 20}})
        return out


def _req(text):
    return {"system": SYSTEM, "messages": msgs(text), "tools": TOOLS, "max_tokens": 10}


def test_create_many_batches_misses_and_skips_hits(tmp_path, monkeypatch):
    live(monkeypatch)
    fake = FakeBatchClient()
    llm = make(tmp_path, fake)
    llm.create(**_req("cached"))  # one sequential call, cached
    out = llm.create_many([_req("cached"), _req("a"), _req("b")])
    assert fake.batches == [2] and len(fake.calls) == 1  # the hit never reached the batch
    assert [o["content"][0]["text"] for o in out[1:]] == ["batch 0", "batch 1"]
    lines = [json.loads(l) for l in (tmp_path / "log.jsonl").read_text().splitlines()]
    batched = [l for l in lines if l.get("batch")]
    assert len(batched) == 2 and batched[0]["est_cost_usd"] == pytest.approx(0.5 * (100 * 0.10 + 20 * 0.50) / 1e6)


def test_create_many_falls_back_per_item(tmp_path, monkeypatch):
    live(monkeypatch)
    fake = FakeBatchClient(fail_index=1)
    out = make(tmp_path, fake).create_many([_req("x"), _req("y")])
    assert out[0]["content"][0]["text"] == "batch 0" and out[1]["content"][0]["text"] == "ok"
    assert len(fake.calls) == 1  # the failed item ran sequentially


def test_create_many_replay_miss_and_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("REPLAY", "1")
    with pytest.raises(ReplayMiss):
        make(tmp_path, FakeBatchClient()).create_many([_req("never")])
    live(monkeypatch)
    with pytest.raises(BudgetExceeded):
        make(tmp_path, FakeBatchClient(), max_calls=1).create_many([_req("p"), _req("q")])


def test_budget_is_shared_across_instances(tmp_path, monkeypatch):
    from agent.llm import Budget
    live(monkeypatch)
    budget = Budget(max_calls=2)
    a, b = (make(tmp_path, FakeClient(), budget=budget) for _ in range(2))
    a.create(**_req("one"))
    b.create(**_req("two"))
    with pytest.raises(BudgetExceeded):
        a.create(**_req("three"))


class CancelBatchClient(FakeClient):
    """Simulates a batch that timed out: one request finished before the cancel, one did not."""

    def run_batch(self, params_list, timeout_s):
        done = {"id": "b0", "type": "message", "role": "assistant", "model": params_list[0]["model"],
                "content": [{"type": "text", "text": "finished in batch"}], "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 1}}
        return [done, None]


def test_partial_batch_results_are_kept_and_logged(tmp_path, monkeypatch):
    live(monkeypatch)
    fake = CancelBatchClient()
    out = make(tmp_path, fake).create_many([_req("p1"), _req("p2")])
    assert out[0]["content"][0]["text"] == "finished in batch" and len(fake.calls) == 1
    lines = [json.loads(l) for l in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert [l["batch"] for l in lines] == [True, False]
