"""Record/replay Claude client with a call budget and a token log (CLAUDE.md BUDGET RULES 1–7).

Every request is cached on disk under sha256(model, system, messages, tools); identical reruns cost $0.
REPLAY=1 forbids live calls. The key comes only from .env as MARGIN_RADAR_API_KEY and is never printed,
logged or cached. Synthetic data — not Opendoor data.
"""
import copy
import hashlib
import json
import logging
import os
import time
from collections.abc import Callable
from pathlib import Path

from dotenv import load_dotenv

from agent.pricing import estimate_cost

KEY_ENV = "MARGIN_RADAR_API_KEY"
log = logging.getLogger("agent.llm")
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = frozenset({"claude-sonnet-5-5"})


class Budget:
    """A live-call budget shared by every LLM instance in one run (BUDGET RULE 7: hard cap per run)."""

    def __init__(self, max_calls: int):
        self.max_calls, self.used = max_calls, 0

    def take(self, n: int = 1) -> None:
        if self.used + n > self.max_calls:
            raise BudgetExceeded(f"MAX_API_CALLS={self.max_calls}: {n} more live call(s) would exceed it "
                                 f"({self.used} used); stopping cleanly")
        self.used += n


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


BATCH_POLL_S = 20
BATCH_TIMEOUT_S = int(os.environ.get("BATCH_TIMEOUT_S", 1800))


class _SDKClient:
    """Thin adapter over the official SDK. Sonnet 5.5 gets the server-side refusal fallback by default
    (sequential calls only: the Batches API rejects the fallback parameter)."""

    def __init__(self, api_key: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)

    def create(self, **kwargs) -> dict:
        if kwargs["model"] in FALLBACK_MODELS:
            response = self._client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **kwargs)
        else:
            response = self._client.messages.create(**kwargs)
        return response.model_dump(mode="json")

    def run_batch(self, params_list: list[dict], timeout_s: int) -> list[dict | None]:
        """Message Batches API (50% price). Returns one response per request, or None for any that did not succeed
        before the timeout (the caller re-runs those sequentially)."""
        batch = self._client.messages.batches.create(
            requests=[{"custom_id": f"r{i}", "params": p} for i, p in enumerate(params_list)])
        deadline, cancelled = time.time() + timeout_s, False
        while self._client.messages.batches.retrieve(batch.id).processing_status != "ended":
            if time.time() > deadline and not cancelled:
                log.warning("batch %s exceeded %ss; cancelling (finished requests are kept)", batch.id, timeout_s)
                self._client.messages.batches.cancel(batch.id)
                cancelled = True  # keep polling: a cancelled batch reaches "ended" with partial results
            time.sleep(BATCH_POLL_S)
        out: list[dict | None] = [None] * len(params_list)
        try:
            for item in self._client.messages.batches.results(batch.id):
                if item.result.type == "succeeded":
                    out[int(item.custom_id[1:])] = item.result.message.model_dump(mode="json")
        except Exception as exc:  # noqa: BLE001 - reported, then every unfinished request runs sequentially
            log.warning("could not read results of batch %s (%s); unfinished requests will run sequentially",
                        batch.id, exc)
        return out


class LLM:
    def __init__(self, model: str, purpose: str, cache_dir: str | Path = "data/llm_cache",
                 token_log: str | Path = "data/token_log.jsonl", max_calls: int | None = None,
                 client_factory: Callable[[], object] | None = None, run_tag: str = "", budget: Budget | None = None):
        self.model, self.purpose, self.run_tag = model, purpose, run_tag
        self.cache_dir = Path(cache_dir) / purpose
        self.token_log = Path(token_log)
        self.budget = budget or Budget(int(os.environ.get("MAX_API_CALLS", 50)) if max_calls is None else max_calls)
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
        self.budget.take(1)
        client = self._client_instance()
        response = client.create(model=self.model, max_tokens=max_tokens, system=system, messages=messages,
                                 tools=tools)
        if not isinstance(response, dict):
            response = response.model_dump(mode="json")
        self._write_cache(path, response)
        self._log(response.get("usage", {}), replay=False)
        return response

    def create_many(self, requests: list[dict]) -> list[dict]:
        """Like create() for many independent requests; cache misses go out as one Message Batch when the client
        supports it (50% price), with per-request sequential fallback."""
        keys = [cache_key(self.model, r["system"], r["messages"], r["tools"]) for r in requests]
        out: list[dict | None] = [None] * len(requests)
        misses = []
        for i, key in enumerate(keys):
            path = self.cache_dir / f"{key}.json"
            if path.exists():
                out[i] = json.loads(path.read_text())
                self._log(out[i].get("usage", {}), replay=True)
            else:
                misses.append(i)
        if misses and os.environ.get("REPLAY", "0") == "1":
            raise ReplayMiss(f"no recorded response for cache key {keys[misses[0]]} ({self.model}, {self.purpose}); "
                             "record it with: REPLAY=0 python -m eval --live (live calls, cost tokens)")
        if misses:
            self.budget.take(len(misses))
        if not misses:
            return out  # type: ignore[return-value]
        client = self._client_instance()
        params = [{"model": self.model, "max_tokens": requests[i]["max_tokens"], "system": requests[i]["system"],
                   "messages": requests[i]["messages"], "tools": requests[i]["tools"]} for i in misses]
        batched = client.run_batch(params, BATCH_TIMEOUT_S) if hasattr(client, "run_batch") and \
            os.environ.get("USE_BATCH", "1") == "1" else [None] * len(misses)
        for i, p, response in zip(misses, params, batched):
            via_batch = response is not None
            if response is None:
                response = client.create(**p)
                if not isinstance(response, dict):
                    response = response.model_dump(mode="json")
            self._write_cache(self.cache_dir / f"{keys[i]}.json", response)
            self._log(response.get("usage", {}), replay=False, batch=via_batch)
            out[i] = response
        return out  # type: ignore[return-value]

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

    def _log(self, usage: dict, replay: bool, batch: bool = False) -> None:
        self.token_log.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": self.model, "purpose": self.purpose,
            "run_tag": self.run_tag, "replay": replay, "batch": batch,
            "input_tokens": 0 if replay else usage.get("input_tokens", 0),
            "output_tokens": 0 if replay else usage.get("output_tokens", 0),
            "cache_creation_input_tokens": 0 if replay else (usage.get("cache_creation_input_tokens") or 0),
            "cache_read_input_tokens": 0 if replay else (usage.get("cache_read_input_tokens") or 0),
        }
        cost = None if replay else estimate_cost(self.model, usage)
        record["est_cost_usd"] = 0.0 if replay else (None if cost is None else cost * (0.5 if batch else 1.0))
        with self.token_log.open("a") as f:
            f.write(json.dumps(record) + "\n")
