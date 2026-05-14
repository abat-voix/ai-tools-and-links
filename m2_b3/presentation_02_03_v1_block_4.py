# Slide: Fallback-цепочка: надёжность через резервирование

import os
from typing import Any


def load_environment() -> None:
    """Загружает .env файл с переменными окружения."""
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость python-dotenv: pip install python-dotenv"
        ) from exc
    load_dotenv()


def get_providers() -> list[dict[str, str]]:
    """Возвращает список провайдеров в порядке приоритета.

    Стратегия fallback:
    1. OpenAI — основной провайдер, самый быстрый
    2. OpenRouter — агрегатор, доступ к разным моделям
    3. Ollama — локальная модель, работает без интернета
    """
    return [
        {
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "model": "gpt-4.1-mini",
        },
        {
            "name": "OpenRouter",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "model": "deepseek/deepseek-chat",
        },
        {
            "name": "Ollama",
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",  # Ollama не требует настоящего ключа
            "model": "qwen3:8b",
        },
    ]


def call_with_fallback(messages: list[dict]) -> str:
    """Пробует провайдеров по порядку. Если все упали — бросает ошибку.

    Каждый провайдер получает timeout=30, чтобы не висеть бесконечно.
    Ошибки накапливаются для финального отчёта.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Установите зависимость openai: pip install openai") from exc

    providers = get_providers()
    errors: list[str] = []

    for provider in providers:
        try:
            client = OpenAI(
                base_url=provider["base_url"],
                api_key=provider["api_key"],
            )
            response = client.chat.completions.create(
                model=provider["model"],
                messages=messages,
                timeout=30,
            )
            print(f"[OK] Ответ от {provider['name']} ({provider['model']})")
            return response.choices[0].message.content
        except Exception as e:
            print(f"[FAIL] {provider['name']}: {e}")
            errors.append(f"{provider['name']}: {e}")
            continue

    raise RuntimeError(
        "Все провайдеры недоступны:\n" + "\n".join(errors)
    )


def main() -> None:
    """Демонстрация fallback-цепочки — автоматическое переключение провайдеров."""
    load_environment()

    messages = [
        {"role": "user", "content": "Что такое fallback в контексте API?"}
    ]

    print("Отправляю запрос с fallback по провайдерам...\n")
    answer = call_with_fallback(messages)
    print(f"\nОтвет: {answer}")


if __name__ == "__main__":
    main()
