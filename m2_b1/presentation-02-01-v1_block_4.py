# Slide: Что ещё можно настроить в первом запросе

from __future__ import annotations

from typing import Any

def build_client() -> Any:
    import os

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

    # OpenAI() — клиент сам достаёт ключ из os.environ["OPENAI_API_KEY"]
    # лучше так не делать в продакшене, а явно передавать api_key=...
    return OpenAI()

def build_request_params() -> dict[str, Any]:
    return {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": "Ты — полезный помощник."},
            {"role": "user", "content": "Объясни декораторы в трех предложениях."},
        ],
        "temperature": 0,
        "top_p": 1.0,
        "max_tokens": 200,
        "stop": ["\n\n"],
        "presence_penalty": 0.3,
        "frequency_penalty": 0.5,
    }


def main() -> None:
    params = build_request_params()
    print("Готовые параметры для запроса chat.completions.create():")
    for key, value in params.items():
        print(f"{key}: {value}")

    client = build_client()
    response = client.chat.completions.create(**params)

    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
