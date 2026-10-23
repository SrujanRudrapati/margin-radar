"""Per-million-token prices (USD), from the claude-api skill's model table (cached 2026-10-06).

Cache writes (5-minute TTL) cost 1.25x input; cache reads 0.1x input. Unknown models return None so reports
print "unknown" instead of a misleading $0.
"""

PRICES_PER_MTOK = {
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_write": 0.125, "cache_read": 0.01},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_write": 2.50, "cache_read": 0.20},
}


def estimate_cost(model: str, usage: dict) -> float | None:
    price = PRICES_PER_MTOK.get(model)
    if price is None:
        return None
    return (
        usage.get("input_tokens", 0) * price["input"]
        + usage.get("output_tokens", 0) * price["output"]
        + (usage.get("cache_creation_input_tokens") or 0) * price["cache_write"]
        + (usage.get("cache_read_input_tokens") or 0) * price["cache_read"]
    ) / 1e6
