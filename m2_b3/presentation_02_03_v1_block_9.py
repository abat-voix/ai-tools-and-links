# Slide: Практика: добавляем надёжность

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


def safe_chat_call(client: Any, messages: list[dict], model: str = "gpt-4.1-mini") -> str | None:
    """Безопасный вызов LLM с обработкой типичных ошибок.

    Обрабатывает:
    - RateLimitError (429) — превышен лимит запросов
    - APIError — ошибки сервера (5xx) и клиента (4xx)
    - APIConnectionError — проблемы с сетью
    - AuthenticationError — невалидный API-ключ

    Возвращает текст ответа или None при ошибке.
    """
    from openai import (
        RateLimitError,
        APIError,
        APIConnectionError,
        AuthenticationError,
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        return response.choices[0].message.content

    except RateLimitError:
        # 429 — слишком много запросов
        print("[ERROR] Превышен лимит запросов. Подождите или уменьшите частоту.")
        return None

    except AuthenticationError:
        # 401 — проблема с API-ключом
        print("[ERROR] Неверный API-ключ. Проверьте OPENAI_API_KEY.")
        return None

    except APIConnectionError:
        # Сеть недоступна
        print("[ERROR] Не удалось подключиться к API. Проверьте интернет.")
        return None

    except APIError as e:
        # Другие ошибки API (500, 503 и т.д.)
        print(f"[ERROR] Ошибка API: {e.status_code} — {e.message}")
        return None


def main() -> None:
    """Демонстрация безопасного вызова с обработкой всех типов ошибок."""
    client = build_client()

    messages = [
        {"role": "user", "content": "Привет! Какие ошибки API бывают чаще всего?"}
    ]

    print("Выполняю безопасный вызов к LLM...\n")
    result = safe_chat_call(client, messages)

    if result:
        print(f"Ответ: {result}")
    else:
        print("Запрос не удался. Смотрите ошибку выше.")


if __name__ == "__main__":
    main()
