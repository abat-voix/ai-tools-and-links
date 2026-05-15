# Slide: Интеграция кеша с LLM-клиентом

from loguru import logger
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from m2_b4.presentation_02_04_v1_block_5 import RedisCache



def build_client() -> OpenAI:
    """Создаёт клиент OpenAI с проверкой API-ключа."""
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Не найден OPENAI_API_KEY в переменных окружения или .env")

    return OpenAI()


def chat_with_cache(
    client: Any,
    messages: list[dict],
    model: str = "gpt-4o-mini",
    temperature: float = 0,
    cache: Any | None = None,
) -> str:
    """Запрос к LLM с кешированием."""
    # 1. Проверяем кеш
    if cache:
        cached = cache.get(model, messages, temperature)
        if cached:
            logger.info("Ответ из кеша")
            return cached

    # 2. Запрос к API
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=50,
    )
    answer = response.choices[0].message.content

    # 3. Сохраняем в кеш (только детерминированные ответы)
    if cache and temperature == 0:
        cache.set(model, messages, temperature, answer)
        logger.info("Сохранено в кеш (tokens: {:d})", response.usage.total_tokens)

    return answer


def main() -> None:
    """Демонстрация интеграции кеша с LLM-клиентом."""

    client = build_client()
    cache = RedisCache(ttl=3600)  # 1 час

    messages = [
        {"role": "system", "content": "Ты сеньор python разработчик"},
        {"role": "user", "content": "Что такое REST API?"},
    ]

    answer1 = chat_with_cache(client, messages, cache=cache)  # API
    logger.info(f"Ответ: {answer1}")

    answer2 = chat_with_cache(client, messages, cache=cache)  # Кеш
    logger.info(f"Ответ: {answer2}")


if __name__ == "__main__":
    main()