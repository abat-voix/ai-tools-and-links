# Slide: Anthropic API: отличия от OpenAI
import os


def main() -> None:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость anthropic: pip install anthropic"
        ) from exc

    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость python-dotenv: pip install python-dotenv"
        ) from exc

    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("Не найден ANTHROPIC_API_KEY в переменных окружения или .env")

    client = Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system="Ты — опытный Python-разработчик.",
        messages=[
            {"role": "user", "content": "Объясни декораторы в 3 предложениях."}
        ],
    )

    print(response.content[0].text)
    print(
        f"Токены: {response.usage.input_tokens} вход "
        f"+ {response.usage.output_tokens} выход"
    )


if __name__ == "__main__":
    main()
