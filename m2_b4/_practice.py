# Практика: кеширование LLM-ответов
# На основе CLI-помощника из блока 2.3 — добавлены:
# 1. Redis-кеш для LLM-ответов (или SimpleCache если нет Docker)
# 2. Команда /cache — статистика кеша
# 3. Команда /clear_cache — очистка кеша
# 4. Замер времени ответа: API vs кеш

import os
import time
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI, RateLimitError, APIError, APIConnectionError
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)

from m2_b4.presentation_02_04_v1_block_1 import SimpleCache
from m2_b4.presentation_02_04_v1_block_5 import RedisCache

load_dotenv()


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

PRICES_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "google/gemini-2.0-flash-001": {"input": 0.10, "output": 0.40},
    "qwen3:8b": {"input": 0.0, "output": 0.0},
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
        price = PRICES_PER_1M_TOKENS.get(model, {"input": 1.00, "output": 3.00})
        cost_input = prompt_tokens / 1_000_000 * price["input"]
        cost_output = completion_tokens / 1_000_000 * price["output"]
        cost = cost_input + cost_output

        self.total_cost += cost
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.request_count += 1

        logger.info(
            "Токены: {}+{} | Стоимость: ${:.6f} | За сессию: ${:.6f}",
            prompt_tokens, completion_tokens, cost, self.total_cost,
        )

    def summary(self) -> None:
        logger.info(
            "Итого за сессию: запросов={}, токенов={}+{}, стоимость=${:.6f}",
            self.request_count, self.total_prompt_tokens,
            self.total_completion_tokens, self.total_cost,
        )


# --------------------------------------------------------------------------
# Кеш: Redis с fallback на SimpleCache
# --------------------------------------------------------------------------

def build_cache() -> RedisCache | SimpleCache:
    """Создаёт Redis-кеш, при недоступности — fallback на SimpleCache."""
    try:
        cache = RedisCache(ttl=3600)
        cache.client.ping()
        logger.info("Кеш: Redis (TTL=3600s)")
        return cache
    except Exception:
        logger.warning("Redis недоступен, используется SimpleCache (in-memory)")
        return SimpleCache(ttl_seconds=3600)


def print_cache_stats(cache: RedisCache | SimpleCache) -> None:
    """Выводит статистику кеша."""
    if isinstance(cache, RedisCache):
        stats = cache.stats()
        logger.info(
            "Cache stats: keys={}, hits={}, misses={}, hit_rate={}",
            stats["keys"], stats["hits"], stats["misses"], stats["hit_rate"],
        )
    else:
        logger.info(
            "Cache stats: keys={}, hits={}, misses={}, hit_rate={:.1f}%",
            len(cache._cache), cache.hits, cache.misses, cache.hit_rate,
        )


def clear_cache(cache: RedisCache | SimpleCache) -> None:
    """Очищает кеш."""
    if isinstance(cache, RedisCache):
        deleted = 0
        for key in cache.client.scan_iter("llm:*"):
            cache.client.delete(key)
            deleted += 1
        logger.info("Удалено ключей из Redis: {}", deleted)
    else:
        cache._cache.clear()
        cache.hits = 0
        cache.misses = 0
        logger.info("SimpleCache очищен")


# --------------------------------------------------------------------------
# Основная логика: вызов LLM с retry, fallback и кешем
# --------------------------------------------------------------------------

def build_client(provider: dict) -> OpenAI:
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


def call_llm_with_retry(client: OpenAI, model: str, messages: list[dict]) -> Any:
    """Вызов LLM с автоматическим retry через tenacity."""
    from openai import RateLimitError, APIStatusError

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((RateLimitError, APIStatusError)),
    )
    def _call() -> Any:
        return client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
        )

    return _call()


def call_with_fallback(
    primary_client: OpenAI,
    primary_model: str,
    fallback_client: OpenAI | None,
    fallback_model: str | None,
    messages: list[dict],
) -> tuple[Any, str]:
    """Пробует основного провайдера, при неудаче — fallback."""
    try:
        return call_llm_with_retry(primary_client, primary_model, messages), primary_model
    except (RateLimitError, APIError, APIConnectionError) as e:
        logger.warning("Основной провайдер недоступен: {}", e)

        if fallback_client and fallback_model:
            logger.info("Переключаюсь на fallback: {}", fallback_model)
            try:
                return call_llm_with_retry(fallback_client, fallback_model, messages), fallback_model
            except Exception as fallback_err:
                raise RuntimeError(
                    f"Оба провайдера недоступны. Fallback: {fallback_err}"
                ) from fallback_err
        raise


def chat_with_cache(
    client: OpenAI,
    model: str,
    messages: list[dict],
    cache: RedisCache | SimpleCache,
    fallback_client: OpenAI | None = None,
    fallback_model: str | None = None,
) -> tuple[str, str, float, Any | None]:
    """Запрос к LLM с кешированием.

    Ключ кеша строится по system-промпту + последнему сообщению пользователя,
    а не по всей истории — иначе один и тот же вопрос никогда не попадёт в кеш.

    Возвращает (ответ, использованная_модель, время_с, usage | None).
    """
    start = time.time()

    # Для кеша берём только system + последнее сообщение пользователя
    cache_messages = [m for m in messages if m["role"] == "system"]
    cache_messages.append(messages[-1])

    # 1. Проверяем кеш
    cached = cache.get(model, cache_messages, temperature=0)
    if cached:
        elapsed = time.time() - start
        logger.info("Из кеша за {:.4f}s", elapsed)
        return cached, model, elapsed, None

    # 2. Запрос к API (передаём полную историю для контекста)
    response, used_model = call_with_fallback(
        client, model, fallback_client, fallback_model, messages,
    )
    answer = response.choices[0].message.content
    elapsed = time.time() - start
    logger.info("API ответ за {:.2f}s", elapsed)

    # 3. Сохраняем в кеш
    cache.set(model, cache_messages, 0, answer)

    return answer, used_model, elapsed, response.usage


# --------------------------------------------------------------------------
# Выбор провайдера
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


# --------------------------------------------------------------------------
# Точка входа
# --------------------------------------------------------------------------

COMMANDS_HELP = "/cache — статистика | /clear_cache — очистка | exit — выход"


def main() -> None:
    provider = choose_provider()
    primary_client = build_client(provider)
    primary_model = provider["model"]

    # Fallback
    fallback_client: OpenAI | None = None
    fallback_model: str | None = None

    if provider["name"] != "Ollama (локальный)":
        try:
            fallback_provider = PROVIDERS["1"]
            fallback_client = build_client(fallback_provider)
            fallback_model = fallback_provider["model"]
            logger.info("Fallback: {} ({})", fallback_provider["name"], fallback_model)
        except Exception:
            logger.warning("Fallback (Ollama) недоступен, работаем без резерва")

    # Кеш
    cache = build_cache()

    # Трекер стоимости
    tracker = SessionCostTracker()

    logger.info("Провайдер: {}, модель: {}", provider["name"], primary_model)
    logger.info("Команды: {}", COMMANDS_HELP)

    messages: list[dict] = [
        {"role": "system", "content": "Отвечай всегда одним словом Привет!"}
    ]

    while True:
        user_input = input("Вы: ").strip()

        if user_input.lower() in ("exit", "quit", "выход"):
            break

        if user_input == "/cache":
            print_cache_stats(cache)
            continue

        if user_input == "/clear_cache":
            clear_cache(cache)
            continue

        if not user_input:
            logger.warning("Пустой ввод пропущен")
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            answer, used_model, elapsed, usage = chat_with_cache(
                client=primary_client,
                model=primary_model,
                messages=messages,
                cache=cache,
                fallback_client=fallback_client,
                fallback_model=fallback_model,
            )
        except RateLimitError:
            logger.error("Превышен лимит запросов. Попробуйте позже")
            messages.pop()
            continue
        except APIConnectionError:
            logger.error("Нет подключения к API. Проверьте интернет")
            messages.pop()
            continue
        except APIError as e:
            logger.error("Ошибка API: {}", e.status_code)
            messages.pop()
            continue
        except Exception as e:
            logger.error("Непредвиденная ошибка: {}", e)
            messages.pop()
            continue

        print(f"Ассистент: {answer}")

        if usage:
            tracker.log_usage(used_model, usage.prompt_tokens, usage.completion_tokens)

        messages.append({"role": "assistant", "content": answer})

    tracker.summary()
    logger.info("Диалог завершён")


if __name__ == "__main__":
    main()
