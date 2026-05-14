# Практика: добавляем надёжность
# На основе диалогового CLI из блока 2.1 — добавлены:
# 1. Обработка ошибок (RateLimitError, APIError, сетевые ошибки)
# 2. Retry через tenacity (повтор при 429 и 5xx)
# 3. Логирование usage и стоимости
# 4. Бонус: fallback на второго провайдера
# 5. Бонус: подсчёт общей стоимости за сессию

import os
from typing import Any


# --------------------------------------------------------------------------
# Конфигурация провайдеров
# --------------------------------------------------------------------------

PROVIDERS = {
    "1": {
        "name": "Ollama (локальный)",
        "api_key": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model": "qwen3:8b",
        "env_key": None,
    },
    "2": {
        "name": "OpenAI",
        "api_key": None,
        "base_url": None,
        "model": "gpt-4.1-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "3": {
        "name": "Groq",
        "api_key": None,
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
        "env_key": "GROQ_API_KEY",
    },
    "4": {
        "name": "OpenRouter",
        "api_key": None,
        "base_url": "https://openrouter.ai/api/v1",
        "model": "google/gemini-2.0-flash-001",
        "env_key": "OPENROUTER_API_KEY",
    },
}

# Примерные цены за 1M токенов (для логирования стоимости)
PRICES_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "google/gemini-2.0-flash-001": {"input": 0.10, "output": 0.40},
    "qwen3:8b": {"input": 0.0, "output": 0.0},  # локальная модель — бесплатно
}


# --------------------------------------------------------------------------
# Трекер стоимости за сессию
# --------------------------------------------------------------------------

class SessionCostTracker:
    """Подсчитывает общую стоимость всех запросов за сессию."""

    def __init__(self) -> None:
        self.total_cost = 0.0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.request_count = 0

    def log_usage(self, model: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Записывает usage одного запроса и выводит стоимость."""
        price = PRICES_PER_1M_TOKENS.get(model, {"input": 1.00, "output": 3.00})

        cost_input = prompt_tokens / 1_000_000 * price["input"]
        cost_output = completion_tokens / 1_000_000 * price["output"]
        cost = cost_input + cost_output

        self.total_cost += cost
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.request_count += 1

        print(
            f"  [Токены: {prompt_tokens}+{completion_tokens} | "
            f"Стоимость: ${cost:.6f} | "
            f"За сессию: ${self.total_cost:.6f}]"
        )

    def summary(self) -> None:
        """Выводит итоговую статистику сессии."""
        print(f"\n{'='*50}")
        print(f"Итого за сессию:")
        print(f"  Запросов: {self.request_count}")
        print(f"  Токенов: {self.total_prompt_tokens} input + {self.total_completion_tokens} output")
        print(f"  Общая стоимость: ${self.total_cost:.6f}")
        print(f"{'='*50}")


# --------------------------------------------------------------------------
# Основная логика: вызов LLM с retry и fallback
# --------------------------------------------------------------------------

def choose_provider() -> dict:
    """Интерактивный выбор основного провайдера."""
    print("Выберите провайдера:")
    for key, p in PROVIDERS.items():
        print(f"  {key}. {p['name']} (модель: {p['model']})")
    while True:
        choice = input("Номер провайдера: ").strip()
        if choice in PROVIDERS:
            return PROVIDERS[choice]
        print(f"Неверный выбор. Введите число от 1 до {len(PROVIDERS)}.")


def build_client(provider: dict) -> Any:
    """Создаёт OpenAI-совместимый клиент для указанного провайдера."""
    from openai import OpenAI

    if provider["env_key"]:
        api_key = os.getenv(provider["env_key"])
        if not api_key:
            raise SystemExit(
                f"Не найден {provider['env_key']} в переменных окружения или .env"
            )
    else:
        api_key = provider["api_key"]

    return OpenAI(api_key=api_key, base_url=provider["base_url"])


def call_llm_with_retry(client: Any, model: str, messages: list[dict]) -> Any:
    """Вызов LLM с автоматическим retry через tenacity.

    Повторяет запрос при:
    - RateLimitError (429) — до 5 раз с экспоненциальной задержкой
    - APIStatusError с кодом 5xx — серверные ошибки
    """
    from tenacity import (
        retry,
        wait_exponential,
        stop_after_attempt,
        retry_if_exception_type,
    )
    from openai import RateLimitError, APIStatusError

    # Функция-предикат: повторяем на 429 и 5xx
    def should_retry(error: BaseException) -> bool:
        if isinstance(error, RateLimitError):
            return True
        if isinstance(error, APIStatusError) and error.status_code >= 500:
            return True
        return False

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((RateLimitError, APIStatusError)),
    )
    def _call() -> Any:
        return client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )

    return _call()


def call_with_fallback(
    primary_client: Any,
    primary_model: str,
    fallback_client: Any | None,
    fallback_model: str | None,
    messages: list[dict],
) -> Any:
    """Пробует основного провайдера, при неудаче — fallback.

    Возвращает stream от первого успешного провайдера.
    """
    from openai import RateLimitError, APIError, APIConnectionError

    try:
        return call_llm_with_retry(primary_client, primary_model, messages), primary_model
    except (RateLimitError, APIError, APIConnectionError) as e:
        print(f"  [Основной провайдер недоступен: {e}]")

        if fallback_client and fallback_model:
            print(f"  [Переключаюсь на fallback: {fallback_model}]")
            try:
                return call_llm_with_retry(fallback_client, fallback_model, messages), fallback_model
            except Exception as fallback_err:
                raise RuntimeError(
                    f"Оба провайдера недоступны. Fallback: {fallback_err}"
                ) from fallback_err
        raise


# --------------------------------------------------------------------------
# Точка входа
# --------------------------------------------------------------------------

def main() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость python-dotenv: pip install python-dotenv"
        ) from exc

    try:
        from openai import OpenAI, RateLimitError, APIError, APIConnectionError
    except ImportError as exc:
        raise SystemExit("Установите зависимость openai: pip install openai") from exc

    try:
        import tenacity  # noqa: F401
    except ImportError as exc:
        raise SystemExit("Установите зависимость tenacity: pip install tenacity") from exc

    load_dotenv()

    # Выбор основного провайдера
    provider = choose_provider()
    primary_client = build_client(provider)
    primary_model = provider["model"]

    # Настройка fallback-провайдера (Ollama как бесплатный локальный запасной вариант)
    fallback_client: Any | None = None
    fallback_model: str | None = None

    # Если основной провайдер — не Ollama, используем Ollama как fallback
    if provider["name"] != "Ollama (локальный)":
        try:
            fallback_provider = PROVIDERS["1"]  # Ollama
            fallback_client = build_client(fallback_provider)
            fallback_model = fallback_provider["model"]
            print(f"Fallback: {fallback_provider['name']} ({fallback_model})")
        except Exception:
            print("Fallback (Ollama) недоступен, работаем без резерва.")

    print(f"\nПровайдер: {provider['name']}, модель: {primary_model}")
    print("Введите сообщение. Для выхода: exit, quit или выход.\n")

    # Инициализация трекера стоимости
    tracker = SessionCostTracker()

    messages: list[dict] = [
        {"role": "system", "content": "Ты — ассистент по языку Python. Отвечай кратко и по делу."}
    ]

    while True:
        user_input = input("Вы: ").strip()
        if user_input.lower() in ("exit", "quit", "выход"):
            break

        if not user_input:
            print("Пустой ввод пропущен.")
            continue

        messages.append({"role": "user", "content": user_input})

        # Вызов с обработкой ошибок
        try:
            stream, used_model = call_with_fallback(
                primary_client, primary_model,
                fallback_client, fallback_model,
                messages,
            )
        except RateLimitError:
            print("  [ERROR] Превышен лимит запросов. Попробуйте позже.")
            messages.pop()  # убираем неотправленное сообщение
            continue
        except APIConnectionError:
            print("  [ERROR] Нет подключения к API. Проверьте интернет.")
            messages.pop()
            continue
        except APIError as e:
            print(f"  [ERROR] Ошибка API: {e.status_code}")
            messages.pop()
            continue
        except Exception as e:
            print(f"  [ERROR] {e}")
            messages.pop()
            continue

        # Читаем stream и выводим ответ
        print("Ассистент: ", end="")
        full_response = ""
        usage = None

        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    print(delta, end="", flush=True)
                    full_response += delta
            if chunk.usage:
                usage = chunk.usage
        print()

        # Логируем usage и стоимость
        if usage:
            tracker.log_usage(used_model, usage.prompt_tokens, usage.completion_tokens)

        messages.append({"role": "assistant", "content": full_response})

    # Итоговая статистика при выходе
    tracker.summary()
    print("Диалог завершён.")


if __name__ == "__main__":
    main()
