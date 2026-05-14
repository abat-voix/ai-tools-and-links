# Slide: Собираем всё вместе: надёжный клиент

import os
import logging
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_environment() -> None:
    """Загружает .env файл с переменными окружения."""
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость python-dotenv: pip install python-dotenv"
        ) from exc
    load_dotenv()


class RobustLLMClient:
    """LLM-клиент с retry, fallback и логированием.

    Объединяет все паттерны надёжности в одном классе:
    - Exponential backoff через tenacity при 429 (rate limit)
    - Fallback-цепочка: если основной провайдер упал — переключаемся на резервный
    - Логирование успехов и ошибок для мониторинга
    """

    def __init__(self) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise SystemExit(
                "Установите зависимость openai: pip install openai"
            ) from exc

        # Провайдеры в порядке приоритета
        self.providers = [
            {
                "name": "OpenAI",
                "client": OpenAI(),
                "model": "gpt-4.1-mini",
            },
            {
                "name": "OpenRouter",
                "client": OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=os.getenv("OPENROUTER_API_KEY", ""),
                ),
                "model": "deepseek/deepseek-chat",
            },
        ]

    def _call_provider(self, client: Any, model: str, messages: list[dict]) -> Any:
        """Вызов одного провайдера с retry через tenacity."""
        try:
            from tenacity import (
                retry,
                wait_exponential,
                stop_after_attempt,
                retry_if_exception_type,
            )
            from openai import RateLimitError
        except ImportError as exc:
            raise SystemExit(
                "Установите зависимость tenacity: pip install tenacity"
            ) from exc

        @retry(
            wait=wait_exponential(min=1, max=30),
            stop=stop_after_attempt(3),
            retry=retry_if_exception_type((RateLimitError,)),
        )
        def _do_call() -> Any:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                timeout=30,
            )

        return _do_call()

    def chat(self, messages: list[dict]) -> str:
        """Отправляет сообщения, пробуя провайдеров по порядку.

        Возвращает текст ответа от первого успешного провайдера.
        Если все провайдеры упали — бросает RuntimeError.
        """
        for provider in self.providers:
            try:
                response = self._call_provider(
                    provider["client"],
                    provider["model"],
                    messages,
                )
                logger.info(
                    f"OK via {provider['name']}, "
                    f"tokens: {response.usage.total_tokens}"
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"{provider['name']} failed: {e}")
                continue

        raise RuntimeError("Все провайдеры недоступны")


def main() -> None:
    """Демонстрация надёжного LLM-клиента с retry и fallback."""
    load_environment()

    llm = RobustLLMClient()

    print("Отправляю запрос через RobustLLMClient...\n")
    answer = llm.chat([
        {"role": "user", "content": "Объясни в одном предложении, зачем нужен fallback."}
    ])
    print(f"Ответ: {answer}")


if __name__ == "__main__":
    main()
