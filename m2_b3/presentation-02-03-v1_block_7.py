# Slide: Usage tracking: алерт на превышение бюджета

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


# Цены за 1M токенов
PRICES_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
}


class BudgetTracker:
    """Трекер бюджета: накапливает расходы и предупреждает при превышении порога.

    В production можно хранить расходы в Redis/БД, а алерты отправлять
    в Slack, Telegram или email.
    """

    def __init__(self, daily_budget: float = 10.0, alert_threshold: float = 0.8):
        self.daily_budget = daily_budget
        self.alert_threshold = alert_threshold  # процент бюджета для алерта
        self.daily_total = 0.0
        self.calls_today = 0

    def track_call(self, model: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Записывает стоимость вызова и проверяет бюджет."""
        price = PRICES_PER_1M_TOKENS.get(model, {"input": 2.00, "output": 8.00})
        cost = (
            prompt_tokens / 1_000_000 * price["input"]
            + completion_tokens / 1_000_000 * price["output"]
        )

        self.daily_total += cost
        self.calls_today += 1

        # Проверяем пороги
        if self.daily_total > self.daily_budget:
            self._send_alert(
                f"ПРЕВЫШЕН бюджет! ${self.daily_total:.4f} / ${self.daily_budget:.2f}"
            )
        elif self.daily_total > self.daily_budget * self.alert_threshold:
            self._send_alert(
                f"Бюджет на {self.daily_total / self.daily_budget * 100:.0f}%: "
                f"${self.daily_total:.4f} / ${self.daily_budget:.2f}"
            )

    def _send_alert(self, message: str) -> None:
        """Отправляет алерт. В production — Slack/Telegram/email."""
        print(f"[ALERT] {message}")

    def report(self) -> None:
        """Печатает сводку расходов за день."""
        print(f"\n--- Сводка ---")
        print(f"Вызовов сегодня: {self.calls_today}")
        print(f"Потрачено: ${self.daily_total:.6f} / ${self.daily_budget:.2f}")
        print(f"Осталось: ${self.daily_budget - self.daily_total:.6f}")


def main() -> None:
    """Демонстрация трекера бюджета с алертами."""
    client = build_client()
    tracker = BudgetTracker(daily_budget=0.01, alert_threshold=0.8)  # маленький бюджет для демо

    messages = [
        {"role": "user", "content": "Скажи одно слово."},
    ]

    print("Делаем несколько запросов для демонстрации трекера бюджета:\n")

    for i in range(3):
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
        )
        usage = response.usage
        tracker.track_call("gpt-4.1-mini", usage.prompt_tokens, usage.completion_tokens)
        print(f"  Запрос {i + 1}: {response.choices[0].message.content.strip()}")

    tracker.report()


if __name__ == "__main__":
    main()
