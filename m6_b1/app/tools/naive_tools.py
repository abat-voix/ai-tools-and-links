"""Инструменты наивного агента: реализации + описания в JSON Schema.

Здесь живут три инструмента, словарь-allowlist `DISPATCH` и список `TOOLS`
с описаниями в формате OpenAI Responses. Агент (`agent_naive.run_agent`)
импортирует `TOOLS` и `DISPATCH` отсюда и сам не знает деталей реализации.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

# Заглушка базы знаний. В дипломном проекте здесь будет вызов
# app/services/rag.py (поиск top-1 фрагмента по реальной коллекции).
_KNOWLEDGE_BASE: dict[str, str] = {
    "возврат": "Возврат товара возможен в течение 14 дней с момента доставки.",
    "доставка": "Доставка по Москве — 1–2 дня, по России — 3–7 рабочих дней.",
    "гарантия": "Гарантия на технику — 12 месяцев с даты покупки, чек обязателен.",
    "оплата": "Доступна оплата картой, по СБП и наличными при получении.",
}


def search_knowledge_base(query: str) -> str:
    """Поиск ответа во внутренней базе знаний по ключевому слову запроса."""
    normalized = query.lower()
    for key, value in _KNOWLEDGE_BASE.items():
        if key in normalized:
            return value
    return "По запросу ничего не найдено."


def get_current_time(timezone: str = "Europe/Moscow") -> str:
    """Текущие дата и время в указанном часовом поясе в формате ISO 8601."""
    now = datetime.now(ZoneInfo(timezone))
    return now.isoformat()


def send_telegram_message(chat_id: str, text: str) -> str:
    """Отправка сообщения клиенту в Telegram (в этом задании — заглушка)."""
    print(f"[TELEGRAM → {chat_id}] {text}")
    return f"Сообщение отправлено в {chat_id}"


# Allowlist: имя инструмента -> реализация. Никаких eval/getattr —
# модель может вызвать только то, что явно перечислено здесь.
DISPATCH = {
    "search_knowledge_base": search_knowledge_base,
    "get_current_time": get_current_time,
    "send_telegram_message": send_telegram_message,
}

# В строгих схемах Responses перечисляем все поля и запрещаем лишние.
TOOLS = [
    {
        "type": "function",
        "name": "search_knowledge_base",
        "description": "Ищет правила возврата, доставки, гарантии и оплаты.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_current_time",
        "description": "Возвращает время в часовом поясе IANA, например Europe/Moscow.",
        "parameters": {
            "type": "object",
            "properties": {"timezone": {"type": "string"}},
            "required": ["timezone"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "send_telegram_message",
        "description": "Печатает учебное сообщение. Внешняя отправка не выполняется.",
        "parameters": {
            "type": "object",
            "properties": {"chat_id": {"type": "string"}, "text": {"type": "string"}},
            "required": ["chat_id", "text"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]
