# Slide: OpenRouter: один API — сотни моделей

import os


def main() -> None:
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
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Не найден OPENROUTER_API_KEY в переменных окружения или .env")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    response = client.chat.completions.create(
        model="tencent/hy3-preview:free",
        messages=[{"role": "user", "content": "Привет! Кто ты?"}],
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
