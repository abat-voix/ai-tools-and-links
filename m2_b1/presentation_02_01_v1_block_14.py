# Slide: Паттерн «один код — любой провайдер»

import os
from typing import Any


def get_client(provider: str = "openai") -> tuple[Any, str]:
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

    configs = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-4.1-mini",
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "tencent/hy3-preview:free",
        },
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",
            "model": "qwen3:8b",
        },
    }

    if provider not in configs:
        available = ", ".join(configs)
        raise SystemExit(f"Неизвестный провайдер '{provider}'. Доступно: {available}")

    cfg = configs[provider]
    if not cfg["api_key"]:
        raise SystemExit(f"Для провайдера '{provider}' не настроен API-ключ")

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
    return client, cfg["model"]


def main() -> None:
    provider = os.getenv("LLM_PROVIDER", "openrouterdgfdf")
    client, model = get_client(provider)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Привет!"}],
    )
    print(f"Провайдер: {provider}")
    print(f"Модель: {model}")
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
