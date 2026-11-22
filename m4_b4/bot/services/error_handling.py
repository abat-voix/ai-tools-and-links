"""Единая обработка ошибок при общении с backend.

Преобразует HTTP/сетевые исключения от backend в человекочитаемые ответы для
пользователя в Telegram. Используется во всех handler'ах, которые гоняют
запросы к chat-сервису (text, fsm, media).

Поддерживает специальный код `moderation_blocked` (403 от backend), который
backend возвращает при срабатывании каскадной модерации.
"""

import logging

import httpx
from aiogram.types import Message

log = logging.getLogger(__name__)


async def handle_backend_error(message: Message, exc: Exception) -> None:
    """Показывает пользователю сообщение об отказе или сбое сервиса."""
    if isinstance(exc, httpx.ConnectError):
        await message.answer("Сервис недоступен, попробуйте позже.")
        return
    if isinstance(exc, httpx.ReadTimeout):
        await message.answer("Ответ занимает слишком долго. Попробуйте короче.")
        return
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 403:
            try:
                body = exc.response.json()
            except ValueError:
                body = {}
            detail = body.get("detail") if isinstance(body, dict) else None
            blocked = isinstance(detail, dict) and detail.get("code") == "moderation_blocked"
            await message.answer("Переформулируйте запрос." if blocked else "Доступ запрещён.")
            return
        if status == 429:
            retry = exc.response.headers.get("Retry-After", "60")
            await message.answer(f"Слишком много запросов. Подождите {retry} сек.")
            return
        if 500 <= status < 600:
            await message.answer("Сервис временно недоступен. Попробуйте позже.")
            return
        await message.answer("Не удалось обработать запрос.")
        return
    if isinstance(exc, httpx.HTTPError):
        await message.answer("Сеть недоступна. Проверьте соединение.")
        return
    log.exception("backend handler failed", exc_info=exc)
    await message.answer("Что-то пошло не так. Попробуйте ещё раз.")
