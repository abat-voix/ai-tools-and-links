# Slide: tiktoken: считаем токены до отправки

from __future__ import annotations


def main() -> None:
    try:
        import tiktoken
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость tiktoken: pip install tiktoken"
        ) from exc

    # Создаём энкодер для конкретной модели
    enc = tiktoken.encoding_for_model("gpt-4.1-mini")

    # Подсчёт токенов в строке
    text = "Привет, как дела? Расскажи о Python."
    tokens = enc.encode(text)
    print(f"Текст: {text}")
    print(f"Токены: {tokens}")
    print(f"Количество: {len(tokens)}")

    # Практическая функция для подсчёта стоимости
    def estimate_cost(messages: list[dict], model: str = "gpt-4.1-mini") -> dict:
        """Оценка стоимости запроса ДО отправки."""
        enc = tiktoken.encoding_for_model(model)
        input_tokens = sum(len(enc.encode(m["content"])) for m in messages)
        # + ~4 токена на каждое сообщение (метаданные)
        input_tokens += len(messages) * 4

        prices = {  # $/1M tokens (актуально на май 2025)
            # GPT-4.1 семейство
            "gpt-4.1": {"input": 2.00, "output": 8.00},
            "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
            "gpt-4.1-nano": {"input": 0.05, "output": 0.20},
            # Reasoning-модели
            "o3": {"input": 10.00, "output": 40.00},
            "o4-mini": {"input": 1.10, "output": 4.40},
            # GPT-4o семейство (legacy)
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        }
        price = prices.get(model, prices["gpt-4.1-mini"])

        return {
            "input_tokens": input_tokens,
            "estimated_input_cost": input_tokens / 1_000_000 * price["input"],
        }

    # Пример использования
    messages = [
        {"role": "system", "content": "Ты — полезный помощник."},
        {"role": "user", "content": "Объясни квантовые вычисления простыми словами."},
    ]
    result = estimate_cost(messages, "gpt-4.1-mini")
    # $0.0000108
    print(f"\nОценка стоимости запроса: {result}")


if __name__ == "__main__":
    main()