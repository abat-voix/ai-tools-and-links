import argparse
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


BASE_SYSTEM_PROMPT = """
Ты ИИ-ассистент поддержки интернет-магазина.

Правила работы:
1. Отвечай по-русски.
2. Будь вежливым и кратким.
3. Если речь о возврате, напоминай про номер заказа.
4. Если речь о доставке, сначала уточняй город и способ доставки.
5. Если пользователь просит юридическую оценку, предупреждай, что это не юридическая консультация.
6. Не выдумывай факты о заказе, если данных нет.
7. Если не хватает данных, задай уточняющий вопрос.
8. Если запрос опасный, откажись и предложи безопасную альтернативу.

База знаний:
- Доставка по Москве: 1-2 дня.
- Доставка по России: 3-7 дней.
- Возврат товара: 14 дней.
- Поддержка работает ежедневно с 09:00 до 21:00.
- Самовывоз доступен только после SMS-подтверждения.

Стиль ответа:
- Сначала короткий ответ по сути.
- Потом 1-2 пункта с уточнениями, если это полезно.
- Не используй канцелярит.
""".strip()

KB_FACTS = [
    "Возврат возможен при сохранении товарного вида и чека либо иного подтверждения покупки.",
    "Если товар с браком, сначала уточняем фото или видео дефекта и номер заказа.",
    "При задержке доставки сначала проверяем город, дату заказа и способ доставки.",
    "Если пользователь спрашивает про самовывоз, напоминаем про SMS-подтверждение готовности.",
    "Если в вопросе фигурирует курьер, уточняем интервал доставки и контактный телефон.",
    "При вопросах об оплате не запрашиваем полные данные карты.",
    "Если вопрос касается гарантии, объясняем базовые условия и предлагаем свериться с карточкой товара.",
    "Если пользователь просит официальный документ, направляем к поддержке с номером заказа.",
    "Если вопрос касается комплектации, советуем сверить коробку и накладную.",
    "Если пользователь пишет эмоционально, сохраняем спокойный и уважительный тон.",
]


def build_long_system_prompt() -> str:
    repeated_facts = "\n".join(
        f"- Политика #{index}: {fact}"
        for index in range(1, 151)
        for fact in KB_FACTS
    )
    return (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        "Расширенная база знаний для демонстрации prompt caching:\n"
        f"{repeated_facts}"
    )


LONG_SYSTEM_PROMPT = build_long_system_prompt()


def make_client(provider: str) -> tuple[OpenAI, str, str]:
    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Не найден GROQ_API_KEY")
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        return client, model, provider

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Не найден OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    return client, model, "openai"


def get_cached_tokens(usage: Any) -> int | None:
    if usage is None:
        return None

    prompt_tokens_details = getattr(usage, "prompt_tokens_details", None)
    if prompt_tokens_details is None:
        return None

    return getattr(prompt_tokens_details, "cached_tokens", None)


def ask(client: OpenAI, model: str, question: str) -> None:
    request_kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": LONG_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "temperature": 0,
    }

    if "gpt" in model:
        request_kwargs["prompt_cache_key"] = "support-demo-v1"

    response = client.chat.completions.create(**request_kwargs)

    text = response.choices[0].message.content
    usage = response.usage
    cached_tokens = get_cached_tokens(usage)

    print(f"\nВопрос: {question}")
    print(f"Ответ: {text}")
    if usage:
        print(f"prompt_tokens={usage.prompt_tokens}")
        print(f"completion_tokens={usage.completion_tokens}")
        print(f"total_tokens={usage.total_tokens}")
    if cached_tokens is not None:
        print(f"cached_tokens={cached_tokens}")
    else:
        print("cached_tokens=недоступно у этого провайдера/ответа")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Демонстрация prompt caching для OpenAI или Groq."
    )
    parser.add_argument(
        "provider",
        nargs="?",
        choices=["openai", "groq"],
        default="openai",
        help="Провайдер LLM: openai или groq",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client, model, provider = make_client(args.provider)

    print(f"Провайдер: {provider}")
    print(f"Модель: {model}")
    print("Делаем 2 запроса с одинаковым длинным system prompt.")
    print("Общий префикс специально увеличен выше порога prompt caching.")
    if provider == "openai":
        print("Для OpenAI второй запрос должен показать cached_tokens > 0.")
        print("В запрос также добавлен стабильный prompt_cache_key.")
    else:
        print("Для Groq поле cached_tokens обычно недоступно.")

    questions = [
        "Какие у вас часы работы?",
        "Я хочу вернуть товар, что для этого нужно?",
    ]

    for question in questions:
        ask(client, model, question)


if __name__ == "__main__":
    main()
