# Slide: Структурированный вывод через промпт

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


def build_json_messages(review_text: str) -> list[dict[str, str]]:
    """Вариант 1: JSON через инструкцию в промпте."""
    return [
        {"role": "system", "content": """Извлеки из текста информацию о товаре.
Ответь СТРОГО в формате JSON:
{
  "name": "название товара",
  "price": число (в рублях),
  "rating": число от 1 до 5,
  "pros": ["плюс 1", "плюс 2"],
  "cons": ["минус 1"]
}
Никакого текста кроме JSON."""},
        {"role": "user", "content": review_text}
    ]


def build_xml_messages(ticket_text: str) -> list[dict[str, str]]:
    """Вариант 2: XML-теги (особенно хорошо работает с Claude)."""
    return [
        {"role": "system", "content": """Проанализируй обращение клиента.

<instructions>
Определи категорию и срочность. Ответь в формате:
<category>billing|technical|feature|other</category>
<urgency>low|medium|high</urgency>
<summary>краткое описание проблемы</summary>
</instructions>"""},
        {"role": "user", "content": ticket_text}
    ]


def main() -> None:
    client = build_client()

    # Вариант 1: JSON-формат
    review_text = (
        "Купил наушники Sony WH-1000XM5 за 32 990 рублей. "
        "Шумоподавление отличное, звук чистый, удобно сидят. "
        "Из минусов — нет складной конструкции. Ставлю 4 из 5."
    )
    print("=== Вариант 1: JSON-формат ===\n")
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=build_json_messages(review_text),
        temperature=0,
        max_tokens=300,
    )
    print(response.choices[0].message.content)

    # Вариант 2: XML-теги
    ticket_text = (
        "Здравствуйте! После обновления приложения перестал работать экспорт отчётов. "
        "Это критично, так как завтра сдача квартального отчёта."
    )
    print("\n=== Вариант 2: XML-теги ===\n")
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=build_xml_messages(ticket_text),
        temperature=2,
        max_tokens=300,
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()