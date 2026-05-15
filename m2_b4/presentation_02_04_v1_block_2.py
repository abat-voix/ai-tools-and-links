# Slide: functools.lru_cache: кеш для прототипов

import os
from functools import lru_cache
from typing import Any
from loguru import logger

from dotenv import load_dotenv
from openai import OpenAI


def build_client() -> OpenAI:
    """Создаёт клиент OpenAI с проверкой API-ключа."""
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Не найден OPENAI_API_KEY в переменных окружения или .env")

    return OpenAI()


@lru_cache(maxsize=128)
def cached_chat(
    system: str, user_message: str, model: str = "gpt-4o-mini"
) -> str:
    """Кешированный запрос к LLM.

    Аргументы должны быть hashable (строки, числа).
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        temperature=0,  # детерминированный ответ для кеша
        max_tokens=20,
    )
    return response.choices[0].message.content


def main() -> None:
    """Демонстрация lru_cache для LLM-запросов."""
    global client
    client = build_client()

    system_prompt = "Ты разработчик на python. Отвечай на мои вопросы только в этом направлении."
    # Первый вызов — идёт в API
    answer1 = cached_chat(system_prompt, "Что такое REST?")
    logger.info("Ответ: {}", answer1)

    # Второй вызов — из кеша (мгновенно)
    answer2 = cached_chat(system_prompt, "Что такое REST?")
    logger.info("Из кеша: {}", answer2)

    # Статистика
    logger.info(cached_chat.cache_info())
    # CacheInfo(hits=1, misses=1, maxsize=128, currsize=1)


if __name__ == "__main__":
    client: Any = None
    main()