import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def _count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def calculate_cost(
    usage: dict[str, Any],
    prices_per_million: dict[str, str],
) -> dict[str, Decimal]:
    """Рассчитать известную стоимость токенов одной попытки Responses."""
    input_tokens = _count(usage.get("input_tokens"), "input_tokens")
    output_tokens = _count(usage.get("output_tokens"), "output_tokens")
    details = usage.get("input_tokens_details") or {}
    read_tokens = _count(details.get("cached_tokens", 0), "cached_tokens")
    write_tokens = _count(details.get("cache_write_tokens", 0), "cache_write_tokens")
    ordinary_tokens = input_tokens - read_tokens - write_tokens
    if ordinary_tokens < 0:
        raise ValueError("Cache reads and writes exceed input_tokens")

    categories = {
        "input": ordinary_tokens,
        "cache_read": read_tokens,
        "output": output_tokens,
    }
    write_details = details.get("cache_write_tokens_details")
    if write_details is None:
        categories["cache_write"] = write_tokens
    else:
        short = _count(write_details.get("ttl_30m_tokens"), "ttl_30m_tokens")
        long = _count(write_details.get("ttl_12h_tokens"), "ttl_12h_tokens")
        if short + long != write_tokens:
            raise ValueError("Write lifetime counts must sum to cache_write_tokens")
        categories["cache_write_30m"] = short
        categories["cache_write_12h"] = long

    costs: dict[str, Decimal] = {}
    for category, tokens in categories.items():
        if tokens == 0:
            costs[category] = Decimal(0)
            continue
        if category not in prices_per_million:
            raise ValueError(f"Missing price for {category}")
        try:
            rate = Decimal(prices_per_million[category])
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid price for {category}") from exc
        if not rate.is_finite() or rate < 0:
            raise ValueError(f"Invalid price for {category}")
        costs[category] = Decimal(tokens) * rate / Decimal(1000000)
    costs["total"] = sum(costs.values(), Decimal(0))
    return costs


if __name__ == "__main__":
    source = Path(__file__).with_name("usage-examples.json")
    for example in json.loads(source.read_text()):
        result = calculate_cost(example["usage"], example["prices_per_million"])
        print(example["name"], json.dumps({k: str(v) for k, v in result.items()}))
