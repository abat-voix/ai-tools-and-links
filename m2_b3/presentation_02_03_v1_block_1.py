# Slide: Exponential Backoff с jitter

from __future__ import annotations

import os
import time
import random
from typing import Any


def build_client() -> Any:
    """Создаёт клиент OpenAI с проверкой зависимостей и API-ключа."""
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость python-dotenv: pip install python-dotenv"
        ) from exc

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Установите зависимость openai: pip install openai") from exc

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Не найден OPENAI_API_KEY в переменных окружения или .env")

    return OpenAI()


def call_with_retry(client: Any, messages: list[dict], max_retries: int = 5) -> Any:
    """Запрос к LLM с exponential backoff и jitter.

    Стратегия:
    - При 429 (RateLimitError) — ждём с экспоненциальной задержкой + jitter
    - При 5xx (серверная ошибка) — повторяем с простой экспоненциальной задержкой
    - При 4xx (клиентская ошибка, кроме 429) — сразу пробрасываем исключение
    """
    from openai import RateLimitError, APIError

    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
            )
        except RateLimitError:
            if attempt == max_retries - 1:
                raise  # последняя попытка — пробрасываем
            # Exponential backoff: 1, 2, 4, 8, 16 секунд
            base_delay = 2 ** attempt
            # Jitter: случайная добавка 0–50% от base, чтобы разнести запросы
            jitter = random.uniform(0, base_delay * 0.5)
            delay = base_delay + jitter
            print(f"429 — жду {delay:.1f}с (попытка {attempt + 1}/{max_retries})")
            time.sleep(delay)
        except APIError as e:
            # 5xx — серверная ошибка, есть смысл повторить
            if e.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            # 4xx — клиентская ошибка, повтор не поможет
            raise


def main() -> None:
    """Демонстрация вызова LLM с автоматическим retry при ошибках."""
    client = build_client()

    messages = [
        {"role": "user", "content": "Объясни что такое exponential backoff в одном предложении."}
    ]

    print("Отправляю запрос с автоматическим retry...")
    response = call_with_retry(client, messages)
    print(f"Ответ: {response.choices[0].message.content}")


if __name__ == "__main__":
    main()