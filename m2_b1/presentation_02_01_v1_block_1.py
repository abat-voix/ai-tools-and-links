# Slide: Безопасность API-ключей

import os
from typing import Any


def load_environment() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость python-dotenv: pip install python-dotenv"
        ) from exc

    load_dotenv()


def build_client() -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Установите зависимость openai: pip install openai") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "Не найден OPENAI_API_KEY. Создайте .env с переменной OPENAI_API_KEY=..."
        )

    return OpenAI(api_key=api_key)


def main() -> None:
    print("Пример безопасной инициализации клиента OpenAI через .env")
    load_environment()
    client = build_client()
    print(f"Клиент создан успешно: {client.__class__.__name__}")


if __name__ == "__main__":
    main()
