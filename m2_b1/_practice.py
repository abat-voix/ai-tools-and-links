# Slide: Практика: пишем код

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError, APIConnectionError

load_dotenv()


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
        "model": "gpt-4o-mini",
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


def build_client(provider: dict) -> Any:
    """Создаёт OpenAI-совместимый клиент для указанного провайдера."""
    if provider["env_key"]:
        api_key = os.getenv(provider["env_key"])
        if not api_key:
            raise SystemExit(
                f"Не найден {provider['env_key']} в переменных окружения или .env"
            )
    else:
        api_key = provider["api_key"]

    return OpenAI(api_key=api_key, base_url=provider["base_url"])


def choose_provider() -> dict:
    print("Выберите провайдера:")
    for key, p in PROVIDERS.items():
        print(f"  {key}. {p['name']} (модель: {p['model']})")
    while True:
        choice = input("Номер провайдера: ").strip()
        if choice in PROVIDERS:
            return PROVIDERS[choice]
        print(f"Неверный выбор. Введите число от 1 до {len(PROVIDERS)}.")


def main() -> None:

    provider = choose_provider()
    client = build_client(provider)
    model = provider["model"]

    fallback_model = None
    fallback_client = None

    if provider["name"] != "Ollama (локальный)":
        try:
            fallback_provider = PROVIDERS["1"]
            fallback_client = build_client(fallback_provider)
            fallback_model = fallback_provider["model"]
            print(f"{provider['name']} доступен. Модель: {fallback_model}")
        except Exception as e:
            print(f"Fallback Ollama недоступен: {e}")

    if fallback_model is None:
        print(f"\nПровайдер: {provider['name']}, модель: {model}")

    messages = [
        {"role": "system", "content": "Ты - ассистент по языку Python. Отвечай только в этом направлении. Больше ничего не говори."}
    ]

    print("Введите сообщение. Для выхода используйте exit, quit или выход.")

    while True:
        user_input = input("\nВы: ").strip()
        if user_input.lower() in ("exit", "quit", "выход"):
            print("Диалог завершён.")
            break

        if not user_input:
            print("Пустой ввод пропущен.")
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            stream, used_model = call_with_fallback(
                primary_client=client,
                primary_model=model,
                fallback_client=fallback_client,
                fallback_model=fallback_model,
                messages=messages,
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

        print("Ассистент: ", end="")
        full_response = ""
        usage = None
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                print(delta, end="", flush=True)
                full_response += delta
            if chunk.usage:
                usage = chunk.usage
        print()  # Печатаем перевод строки после завершения ответа

        if usage:
            print(
                f"[Токены: запрос={usage.prompt_tokens}, "
                f"ответ={usage.completion_tokens}, "
                f"всего={usage.total_tokens}]"
            )

        messages.append({"role": "assistant", "content": full_response})


if __name__ == "__main__":
    main()