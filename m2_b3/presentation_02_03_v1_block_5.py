# Slide: Prompt Caching: экономим до 90%

import os
from typing import Any


def build_client() -> Any:
    """Создаёт клиент Anthropic с проверкой зависимостей и API-ключа."""
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость python-dotenv: pip install python-dotenv"
        ) from exc

    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise SystemExit(
            "Установите зависимость anthropic: pip install anthropic"
        ) from exc

    load_dotenv()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("Не найден ANTHROPIC_API_KEY в переменных окружения или .env")

    return Anthropic()


# Длинный system prompt для демонстрации кеширования.
# В реальном проекте это может быть инструкция на 5000+ токенов,
# база знаний или шаблон ответа.
LONG_SYSTEM_PROMPT = """\
Ты — экспертный ассистент техподдержки SaaS-платформы «CloudDocs».

Основные правила:
1. Всегда здоровайся и представляйся
2. При технических проблемах — сначала уточни версию браузера и ОС
3. При вопросах о billing — запроси номер аккаунта
4. Не разглашай внутреннюю информацию о системе
5. Если не знаешь ответа — передай на L2 поддержку

База знаний (краткая):
- Сброс пароля: Настройки → Безопасность → Сменить пароль
- Двухфакторная аутентификация: Настройки → Безопасность → 2FA
- Экспорт данных: Документы → Выбрать все → Экспорт → ZIP
- Лимиты: бесплатный план — 100 документов, Pro — без лимита
- API: документация на docs.clouddocs.example/api/v2

(Представьте, что здесь ещё 4000 токенов инструкций и FAQ...)
"""


def main() -> None:
    """Демонстрация Prompt Caching в Anthropic API.

    cache_control: {"type": "ephemeral"} говорит API кешировать этот блок.
    - Первый запрос: полная цена за все input-токены
    - Повторные запросы: cached-токены стоят на 90% дешевле!

    Это особенно выгодно когда:
    - Один и тот же длинный system prompt используется в каждом запросе
    - Много пользователей задают вопросы одному боту
    - Контекст (база знаний) не меняется между запросами
    """
    client = build_client()

    # Первый запрос — system prompt кешируется
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        system=[
            {
                "type": "text",
                "text": LONG_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # Кешировать этот блок!
            }
        ],
        messages=[{"role": "user", "content": "Как сбросить пароль?"}],
    )

    print(f"Ответ: {response.content[0].text}")
    print(f"\nИспользование токенов:")
    print(f"  Input tokens: {response.usage.input_tokens}")
    print(f"  Output tokens: {response.usage.output_tokens}")

    # Второй запрос — system prompt берётся из кеша (на 90% дешевле!)
    response2 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        system=[
            {
                "type": "text",
                "text": LONG_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": "Какие лимиты у бесплатного плана?"}],
    )

    print(f"\nВторой ответ: {response2.content[0].text}")
    print(f"  Input tokens: {response2.usage.input_tokens}")
    print(f"  Output tokens: {response2.usage.output_tokens}")
    # При повторном запросе cache_read_input_tokens покажет сколько взято из кеша


if __name__ == "__main__":
    main()
