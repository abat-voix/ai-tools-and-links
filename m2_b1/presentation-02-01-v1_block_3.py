# Slide: OpenAI API: первый запрос


from typing import Any
import os

try:
    from dotenv import load_dotenv
except ImportError as exc:
    raise SystemExit(
        "Установите зависимость python-dotenv: pip install python-dotenv"
    ) from exc


def build_messages() -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "Ты — опытный Python-разработчик."},
        {"role": "user", "content": "Объясни декораторы в 3 предложениях."},
    ]


def build_client() -> Any:

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Установите зависимость openai: pip install openai") from exc

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Не найден OPENAI_API_KEY в переменных окружения или .env")

    # OpenAI() — клиент сам достаёт ключ из os.environ["OPENAI_API_KEY"]
    # лучше так не делать в продакшене, а явно передавать api_key=...
    return OpenAI(
        api_key=api_key,
    )


def main() -> None:
    client = build_client()
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=build_messages(),
        temperature=2,
        max_tokens=200,
    )

    print(response.choices[0].message.content)
    print(
        f"Токены: {response.usage.prompt_tokens} вход "
        f"+ {response.usage.completion_tokens} выход "
        f"= {response.usage.total_tokens} всего"
    )


if __name__ == "__main__":
    main()
