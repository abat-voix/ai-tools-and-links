from unittest.mock import AsyncMock

import httpx
import pytest

from bot.services.error_handling import handle_backend_error


@pytest.mark.parametrize(
    ("status", "body", "headers", "expected"),
    [
        (403, '{"detail":{"code":"moderation_blocked"}}', {}, "Переформулируйте запрос."),
        (403, '{"detail":"Запрещено"}', {}, "Доступ запрещён."),
        (403, "not json", {}, "Доступ запрещён."),
        (429, "", {"Retry-After": "15"}, "Слишком много запросов. Подождите 15 сек."),
    ],
)
async def test_backend_error_reply(status: int, body: str, headers: dict[str, str], expected: str) -> None:
    request = httpx.Request("POST", "http://support.local/chats/chat/messages")
    response = httpx.Response(status, text=body, headers=headers, request=request)
    message = AsyncMock()
    with pytest.raises(httpx.HTTPStatusError) as error:
        response.raise_for_status()
    await handle_backend_error(message, error.value)
    message.answer.assert_awaited_once_with(expected)
