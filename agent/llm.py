"""Record/replay Claude client with a call budget and a token log (CLAUDE.md BUDGET RULES 1–7).

Every request is cached on disk under sha256(model, system, messages, tools); identical reruns cost $0.
REPLAY=1 forbids live calls. The key comes only from .env as MARGIN_RADAR_API_KEY and is never printed,
logged or cached. Synthetic data — not Opendoor data.
"""
import copy
import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path

from dotenv import load_dotenv

from agent.pricing import estimate_cost

KEY_ENV = "MARGIN_RADAR_API_KEY"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = frozenset({"claude-sonnet-5-5"})


class ReplayMiss(RuntimeError):
    pass


class BudgetExceeded(RuntimeError):
    pass


class MissingKey(RuntimeError):
    pass


def cache_key(model: str, system, messages, tools) -> str:
    payload = json.dumps({"model": model, "system": system, "messages": messages, "tools": tools},
                         sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def with_prompt_caching(system: list[dict], tools: list[dict]) -> tuple[list[dict], list[dict]]:
    system, tools = copy.deepcopy(system), copy.deepcopy(tools)
    if system:
        system[-1]["cache_control"] = {"type": "ephemeral"}
    if tools:
        tools[-1]["cache_control"] = {"type": "ephemeral"}
    return system, tools


class _SDKClient:
    """Thin adapter over the official SDK. Sonnet 5.5 gets the server-side refusal fallback by default."""

    def __init__(self, api_key: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)

    def create(self, **kwargs) -> dict:
        if kwargs["model"] in FALLBACK_MODELS:
            response = self._client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **kwargs)
        else:
            response = self._client.messages.create(**kwargs)
        return response.model_dump(mode="json")


class LLM:
    def __init__(self, model: str, purpose: str, cache_dir: str | Path = "data/llm_cache",
                 token_log: str | Path = "data/token_log.jsonl", max_calls: int | None = None,
                 client_factory: Callable[[], object] | None = None, run_tag: str = ""):
        self.model, self.purpose, self.run_tag = model, purpose, run_tag
        self.cache_dir = Path(cache_dir) / purpose
        self.token_log = Path(token_log)
        self.max_calls = int(os.environ.get("MAX_API_CALLS", 50)) if max_calls is None else max_calls
        self.live_calls = 0
        self._factory = client_factory
        self._client = None

    def create(self, *, system: list[dict], messages: list[dict], tools: list[dict], max_tokens: int) -> dict:
        key = cache_key(self.model, system, messages, tools)
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            response = json.loads(path.read_text())
            self._log(response.get("usage", {}), replay=True)
            return response
        if os.environ.get("REPLAY", "0") == "1":
            raise ReplayMiss(f"no recorded response for cache key {key} ({self.model}, {self.purpose}); "
                             f"record it with: REPLAY=0 python -m agent brief ... (live call, costs tokens)")
        if self.live_calls >= self.max_calls:
            raise BudgetExceeded(f"MAX_API_CALLS={self.max_calls} reached; stopping before another live call")
        client = self._client_instance()
        self.live_calls += 1
        response = client.create(model=self.model, max_tokens=max_tokens, system=system, messages=messages,
                                 tools=tools)
        if not isinstance(response, dict):
            response = response.model_dump(mode="json")
        self._write_cache(path, response)
        self._log(response.get("usage", {}), replay=False)
        return response

    def _client_instance(self):
        if self._client is None:
            if self._factory is not None:
                self._require_key()
                self._client = self._factory()
            else:
                self._client = _SDKClient(self._require_key())
        return self._client

    def _require_key(self) -> str:
        load_dotenv(override=False)
        key = os.environ.get(KEY_ENV)
        if not key:
            raise MissingKey(f"{KEY_ENV} is not set; add it to .env (never commit it)")
        return key

    def _write_cache(self, path: Path, response: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(response, sort_keys=True, indent=1))
        tmp.replace(path)

    def _log(self, usage: dict, replay: bool) -> None:
        self.token_log.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": self.model, "purpose": self.purpose,
            "run_tag": self.run_tag, "replay": replay,
            "input_tokens": 0 if replay else usage.get("input_tokens", 0),
            "output_tokens": 0 if replay else usage.get("output_tokens", 0),
            "cache_creation_input_tokens": 0 if replay else (usage.get("cache_creation_input_tokens") or 0),
            "cache_read_input_tokens": 0 if replay else (usage.get("cache_read_input_tokens") or 0),
        }
        record["est_cost_usd"] = 0.0 if replay else estimate_cost(self.model, usage)
        with self.token_log.open("a") as f:
            f.write(json.dumps(record) + "\n")
