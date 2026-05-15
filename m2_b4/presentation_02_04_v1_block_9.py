# Slide: Инвалидация кеша — очистка по паттерну

from loguru import logger

def flush_llm_cache(cache: object, pattern: str = "llm:*") -> int:
    """Удаляет все ключи LLM-кеша из Redis по паттерну.

    Использует SCAN для безопасного обхода ключей без блокировки.
    Возвращает количество удалённых ключей.
    """
    deleted = 0
    for key in cache.client.scan_iter(pattern):
        cache.client.delete(key)
        deleted += 1
    return deleted


def main() -> None:
    """Демонстрация очистки кеша по паттерну."""
    from presentation_02_04_v1_block_5 import RedisCache

    cache = RedisCache(ttl=3600)

    # Сохраняем тестовые данные
    messages = [{"role": "user", "content": "Тест"}]
    cache.set("gpt-4o-mini", messages, 0, "Тестовый ответ")

    logger.info("Ключей до очистки:  {}", cache.client.dbsize())

    deleted = flush_llm_cache(cache)
    logger.info("Удалено ключей:     {}", deleted)
    logger.info("Ключей после:       {}", cache.client.dbsize())


if __name__ == "__main__":
    main()