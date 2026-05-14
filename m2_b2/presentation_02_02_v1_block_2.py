# Slide: Reasoning-модели: как они «думают» в API

import os
from typing import Any


def build_client() -> Any:
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


def main() -> None:
    client = build_client()

    response = client.responses.create(
        model="gpt-5",
        input="Проверь, выгоднее ли нам кэшировать этот endpoint при 50k запросов в день.",
        reasoning={
            "effort": "low",
            "summary": "auto",
        }
    )

    print("Ответ модели:")
    print(response.output_text)

    # Показываем usage — видно, сколько reasoning-токенов потрачено
    print(f"\nТокены: input={response.usage.input_tokens}, "
          f"output={response.usage.output_tokens}, "
          f"reasoning={response.usage.output_tokens_details.reasoning_tokens}")


if __name__ == "__main__":
    main()
