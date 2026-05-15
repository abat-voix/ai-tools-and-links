# Slide: Инвалидация кеша — TTL

from loguru import logger

# TTL (Time To Live) — самый простой способ инвалидации.
# Redis автоматически удаляет ключ по истечении TTL.

# Пример: кеш на 1 час
# cache.set(key, value, ttl=3600)  # через час — удалится

# Рекомендации по TTL:
# - Справочные данные (документация, определения) → 24 часа
# - Аналитика, отчёты → 1–4 часа
# - Персонализированные ответы → 15–30 минут
# - Данные, зависящие от времени → без кеша или 1–5 минут


def main() -> None:
    """Демонстрация TTL-инвалидации на примере SimpleCache."""
    import time

    from presentation_02_04_v1_block_1 import SimpleCache

    cache = SimpleCache(ttl_seconds=2)  # TTL = 2 секунды для демонстрации
    model = "gpt-4o-mini"
    messages = [{"role": "user", "content": "Привет!"}]

    cache.set(model, messages, 0, "Ответ из кеша")

    # Сразу — hit
    logger.info("До TTL:    {}", cache.get(model, messages))

    # Ждём истечения TTL
    time.sleep(3)

    # После TTL — miss
    logger.info("После TTL: {}", cache.get(model, messages))


if __name__ == "__main__":
    main()