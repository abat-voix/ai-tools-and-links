# Slide: tenacity: retry в 3 строки

from __future__ import annotations

import os
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


def make_call_llm(client: Any) -> Any:
    """Создаёт функцию вызова LLM с декоратором tenacity для автоматического retry.

    tenacity позволяет декларативно задать стратегию повторов:
    - wait_exponential: задержка растёт экспоненциально (1, 2, 4, 8... до 60с)
    - stop_after_attempt: максимальное количество попыток
    - retry_if_exception_type: повторяем только при определённых ошибках (429)
    """
    try:
        from tenacity import (
            retry,
            wait_exponential,
            stop_after_attempt,
            retry_if_exception_type,
        )
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость tenacity: pip install tenacity"
        ) from exc

    from openai import RateLimitError

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=60),  # 1, 2, 4, 8... до 60с
        stop=stop_after_attempt(5),                           # максимум 5 попыток
        retry=retry_if_exception_type((RateLimitError,)),     # только на 429
    )
    def call_llm(messages: list[dict], model: str = "gpt-4.1-mini") -> Any:
        """Запрос к LLM с автоматическим retry через tenacity."""
        return client.chat.completions.create(
            model=model,
            messages=messages,
        )

    return call_llm


def main() -> None:
    """Демонстрация retry через tenacity — выглядит как обычный вызов функции."""
    client = build_client()
    call_llm = make_call_llm(client)

    # Использование — как обычная функция, retry скрыт внутри:
    response = call_llm([
        {"role": "user", "content": "Привет! Что такое tenacity?"}
    ])
    print(f"Ответ: {response.choices[0].message.content}")


if __name__ == "__main__":
    main()