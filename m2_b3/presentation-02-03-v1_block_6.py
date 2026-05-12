# Slide: Usage tracking: считаем деньги

from __future__ import annotations

import os
from datetime import datetime
from typing import Any


def build_client() -> Any:
    """Создаёт клиент OpenAI с проверкой зависимостей и API-ключа."""
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


# Цены за 1M токенов (примерные, май 2025)
# В production лучше хранить в конфиге и обновлять при смене тарифов
PRICES_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
}


def call_and_log(client: Any, messages: list[dict], model: str = "gpt-4.1-mini") -> Any:
    """Выполняет запрос к LLM и логирует стоимость.

    Считает примерную стоимость запроса на основе usage-данных из ответа.
    В production эти данные отправляют в Prometheus, Datadog или БД
    для мониторинга расходов.
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    # Получаем цены для модели (или дефолтные)
    price = PRICES_PER_1M_TOKENS.get(model, {"input": 2.00, "output": 8.00})

    # Считаем стоимость
    usage = response.usage
    cost_input = usage.prompt_tokens / 1_000_000 * price["input"]
    cost_output = usage.completion_tokens / 1_000_000 * price["output"]
    total_cost = cost_input + cost_output

    # Формируем лог-запись
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "cost_usd": round(total_cost, 6),
    }

    print(
        f"[Cost] {log_entry['cost_usd']:.6f} USD | "
        f"{usage.prompt_tokens} input + {usage.completion_tokens} output tokens | "
        f"model={model}"
    )

    # В production: отправить в Prometheus / записать в БД / Datadog
    return response


def main() -> None:
    """Демонстрация трекинга расходов на API-вызовы."""
    client = build_client()

    messages = [
        {"role": "system", "content": "Отвечай кратко, в одно предложение."},
        {"role": "user", "content": "Зачем отслеживать стоимость API-вызовов?"},
    ]

    print("Запрос к LLM с логированием стоимости:\n")
    response = call_and_log(client, messages)
    print(f"\nОтвет: {response.choices[0].message.content}")

    # Совет: в production добавьте алерт на превышение бюджета
    # daily_budget = 10.0  # $10/день
    # if daily_total > daily_budget * 0.8:
    #     send_alert(f"Бюджет на 80%: ${daily_total:.2f}")


if __name__ == "__main__":
    main()
