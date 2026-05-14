# Slide: tenacity: логирование retry-попыток

from __future__ import annotations

import os
import logging
from typing import Any

# Настраиваем логирование, чтобы видеть попытки retry в консоли
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


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
    """Создаёт функцию вызова LLM с retry и логированием каждой попытки.

    before_sleep_log — колбэк tenacity, который логирует информацию
    перед каждым sleep (т.е. между retry-попытками).
    Это помогает в production отслеживать, когда и почему происходят повторы.
    """
    try:
        from tenacity import (
            retry,
            wait_exponential,
            stop_after_attempt,
            retry_if_exception_type,
            before_sleep_log,
        )
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость tenacity: pip install tenacity"
        ) from exc

    from openai import RateLimitError

    @retry(
        wait=wait_exponential(min=1, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((RateLimitError,)),
        # before_sleep логирует WARNING перед каждой паузой между попытками:
        # "Retrying call_llm in 2.0 seconds as it raised RateLimitError..."
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def call_llm(messages: list[dict], model: str = "gpt-4.1-mini") -> Any:
        """Запрос к LLM с retry и логированием попыток."""
        return client.chat.completions.create(
            model=model,
            messages=messages,
        )

    return call_llm


def main() -> None:
    """Демонстрация retry с логированием — в консоли видны WARNING при повторах."""
    client = build_client()
    call_llm = make_call_llm(client)

    response = call_llm([
        {"role": "user", "content": "Привет! Как дела?"}
    ])
    print(f"Ответ: {response.choices[0].message.content}")


if __name__ == "__main__":
    main()
