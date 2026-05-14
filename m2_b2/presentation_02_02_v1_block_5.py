# Slide: Управление контекстом: приоритеты

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


def summarize_history(client: Any, messages: list[dict]) -> str:
    """Сжимает старую историю диалога в короткое summary."""
    msgs = [
            {
                "role": "system",
                "content": (
                    "Суммаризируй историю диалога для техподдержки. "
                    "Сохрани только факты, уже выполненные шаги проверки "
                    "и важные ограничения. "
                    "Не добавляй ничего от себя. "
                    "Ответ — 2–4 коротких предложения."
                ),
            },
            {
                "role": "user",
                "content": "\n".join(
                    f"{m['role']}: {m['content']}"
                    for m in messages
                    if m["role"] != "system"
                ),
            },
        ]
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=msgs,
    )
    return response.choices[0].message.content.strip()


def main() -> None:
    client = build_client()

    messages = [
        {"role": "system", "content": "Ты — ассистент техподдержки."},
        {"role": "user", "content": "Мне не приходит письмо подтверждения."},
        {"role": "assistant", "content": "Проверьте папку Спам."},
        {"role": "user", "content": "Проверил, там пусто."},
        {"role": "assistant", "content": "Попробуйте другой email."},
        {"role": "user", "content": "Пробовал, тоже не приходит."},
        {"role": "assistant", "content": "Есть ли закономерность?"},
        {"role": "user", "content": "Да, проблема только у аккаунтов с доменом company.ru."},
    ]

    summary = summarize_history(client, messages[1:])
    print(f"Summary старой истории:\n{summary}\n")

    messages = [
        messages[0],  # исходный system prompt
        {"role": "system", "content": f"Краткое содержание предыдущего диалога: {summary}"},
        {"role": "user", "content": "Что проверить дальше?"},
    ]

    print("Сжатые сообщения для следующего запроса:")
    for m in messages:
        print(f"  {m['role']}: {m['content']}")


if __name__ == "__main__":
    main()
