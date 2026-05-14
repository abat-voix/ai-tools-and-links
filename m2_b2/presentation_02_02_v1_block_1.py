# Slide: Few-shot: обучение на примерах

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


def build_messages() -> list[dict[str, str]]:
    """Few-shot классификатор тикетов поддержки."""
    return [
        {"role": "system", "content": """
        Ты классифицируешь тикеты поддержки.
        Верни JSON: {"label":"billing|technical|feature|other","urgency":"low|medium|high"}
        Если в сообщении есть несколько тем, выбирай главную причину обращения.
        """},

        # Типовой billing-кейс
        {"role": "user", "content": "С меня дважды списали оплату за март, верните деньги."},
        {"role": "assistant", "content": '{"label":"billing","urgency":"high"}'},

        # Пограничный кейс: и баг, и эмоции, но главная проблема — неработающий продукт
        {"role": "user", "content": "После обновления приложение вылетает при входе. "
                                     "Это уже третий день, работать невозможно."},
        {"role": "assistant", "content": '{"label":"technical","urgency":"high"}'},

        # Негативный кейс: просьба о новой функции, а не баг
        {"role": "user", "content": "Добавьте, пожалуйста, экспорт в Excel и webhook в API."},
        {"role": "assistant", "content": '{"label":"feature","urgency":"low"}'},

        # Реальный запрос
        {"role": "user", "content": "Всё работает!"}
    ]
    # Ожидаемый ответ: {"label":"billing","urgency":"medium|high"}


def main() -> None:
    client = build_client()
    messages = build_messages()

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0,
        max_tokens=100,
    )

    print("Запрос: Поддержка отвечает быстро, но деньги за отменённую подписку так и не вернулись.")
    print(f"Ответ модели: {response.choices[0].message.content}")
    print(f"Ожидаемый:    " + '{"label":"other","urgency":"low"}')


if __name__ == "__main__":
    main()
