# Slide: Exact match: простейший кеш (dict)

import hashlib
import json
import time
from loguru import logger


class SimpleCache:
    """In-memory кеш с TTL."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._cache: dict[str, tuple[str, float]] = {}
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    def _make_key(
        self, model: str, messages: list[dict], temperature: float = 0
    ) -> str:
        """Ключ = хеш(модель + параметры + промпт)."""
        data = json.dumps(
            {"model": model, "messages": messages, "temperature": temperature},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def get(self, model: str, messages: list[dict], temperature: float = 0) -> str | None:
        key = self._make_key(model, messages, temperature)
        if key in self._cache:
            value, created_at = self._cache[key]
            if time.time() - created_at < self.ttl:
                self.hits += 1
                return value
            del self._cache[key]  # TTL истёк
        self.misses += 1
        return None

    def set(self, model: str, messages: list[dict], temperature: float, response: str) -> None:
        key = self._make_key(model, messages, temperature)
        self._cache[key] = (response, time.time())

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total * 100 if total > 0 else 0.0


def main() -> None:
    """Демонстрация работы SimpleCache."""
    cache = SimpleCache(ttl_seconds=60)
    model = "gpt-4o-mini"
    messages = [{"role": "user", "content": "Привет!"}]

    # Первый запрос — miss
    result = cache.get(model, messages)
    logger.info("GET (miss): {}", result)

    # Сохраняем ответ
    cache.set(model, messages, 0, "Привет! Чем могу помочь?")

    # Повторный запрос — hit
    result = cache.get(model, messages)
    logger.info("GET (hit):  {}", result)

    logger.info("Hit rate:   {:.1f}%", cache.hit_rate)


if __name__ == "__main__":
    main()