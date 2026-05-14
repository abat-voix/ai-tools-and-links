# Slide: Streaming: ответ по частям
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

    return OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )


def main() -> None:
    client = build_client()

    prompt = "Напиши рецепт борща"

    print("Обычный запрос:\n")
    response = client.chat.completions.create(
        model="gemma3:1b",
        messages=[{"role": "user", "content": prompt}],
    )
    print(response.choices[0].message.content)

    print("\nStreaming:\n")
    stream = client.chat.completions.create(
        model="gemma3:1b",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    full_response = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            print(delta, end="", flush=True)
            full_response += delta

    print("\n\nПолный streaming-ответ собран, длина:", len(full_response))


if __name__ == "__main__":
    main()
