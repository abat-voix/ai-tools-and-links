# Slide: Метрики кеша

from loguru import logger

def print_cache_report(cache: object, avg_tokens: int = 500) -> None:
    """Выводит отчёт о работе кеша с оценкой экономии.

    Args:
        cache: экземпляр RedisCache с методом stats().
        avg_tokens: среднее количество токенов на запрос (для расчёта экономии).
    """
    stats = cache.stats()
    cost_per_token = 2.50 / 1_000_000  # GPT-4o input price

    logger.info("=== Cache Report ===")
    logger.info("Keys in cache: {}", stats["keys"])
    logger.info("Hits:          {}", stats["hits"])
    logger.info("Misses:        {}", stats["misses"])
    logger.info("Hit rate:      {}", stats["hit_rate"])

    saved = stats["hits"] * avg_tokens * cost_per_token
    logger.info("Estimated savings: ${:.4f}", saved)


def main() -> None:
    """Демонстрация отчёта по метрикам кеша."""
    from presentation_02_04_v1_block_5 import RedisCache

    cache = RedisCache(ttl=3600)
    print_cache_report(cache)


if __name__ == "__main__":
    main()