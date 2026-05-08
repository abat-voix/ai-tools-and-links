# Slide: Chain-of-thought: «подумай шаг за шагом»

from __future__ import annotations

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


def build_messages(task: str) -> list[dict[str, str]]:
    """Chain-of-Thought через system prompt с analysis scratchpad."""
    return [
        {"role": "system", "content": """
        Ты — аналитик.
        Сначала выполни краткий analysis scratchpad в 3–5 шагах.
        Потом дай final answer отдельно.
        Если задача простая, не раздувай рассуждение.
        """},
                {"role": "user", "content": f"""
        Оцени, какую модель выбрать для задачи: {task}
        
        Верни ответ в формате:
        analysis:
        - шаг 1
        - шаг 2
        
        final:
        краткая рекомендация
        """}
            ]


def main() -> None:
    client = build_client()
    task = "классификация тикетов поддержки на 4 категории, 10k запросов в день"

    messages = build_messages(task)
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.3,
        max_tokens=500,
    )

    print(f"Задача: {task}\n")
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()