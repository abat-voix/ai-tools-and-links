"""Контрактные тесты BackendClient через httpx.MockTransport.

Не дёргают реальный backend — проверяют, что бот правильно сериализует
запросы и парсит SSE-ответ chat-сервиса.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from bot.services.backend_client import BackendClient
from bot.services.error_handling import handle_backend_error


@pytest.mark.asyncio
@pytest.mark.parametrize("tail", [b'data: {"type":"error","code":"generation_failed"}\n\n', b""])
async def test_failed_or_unterminated_stream_is_not_success(tail):
    body = b'data: {"type":"token","delta":"partial"}\n\n' + tail
    transport = httpx.MockTransport(lambda _: httpx.Response(
        200, content=body, headers={"Content-Type": "text/event-stream"},
    ))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        client = BackendClient(http)
        with pytest.raises(RuntimeError, match="stream"):
            [event async for event in client.send_message(uuid4(), "hello")]


@pytest.mark.parametrize(("status", "code", "expected"), [
    (403, "moderation_blocked", "Переформулируйте запрос."),
    (429, "rate_limit", "Слишком много запросов. Подождите 12 сек."),
])
async def test_http_rejection_before_stream_can_be_shown_to_user(status, code, expected):
    class ErrorBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield json.dumps({"detail": {"code": code}}).encode()

    transport = httpx.MockTransport(lambda _: httpx.Response(
        status, stream=ErrorBody(), headers={"Retry-After": "12"},
    ))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        client = BackendClient(http)
        with pytest.raises(httpx.HTTPStatusError) as rejection:
            [event async for event in client.send_message(uuid4(), "hello")]

    message = SimpleNamespace(answer=AsyncMock())
    await handle_backend_error(message, rejection.value)
    message.answer.assert_awaited_once_with(expected)


@pytest.mark.asyncio
async def test_get_or_create_chat():
    chat_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/chats"
        assert request.method == "POST"
        body = json.loads(request.content.decode())
        assert body["owner_external_id"] == "tg-123"
        assert body["interface"] == "telegram"
        return httpx.Response(200, json={"chat_id": str(chat_id)})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://x") as c:
        client = BackendClient(c)
        result = await client.get_or_create_chat("tg-123", "telegram")
        assert result == chat_id


@pytest.mark.asyncio
async def test_send_message_parses_sse():
    sse_body = (
        b'data: {"type":"token","delta":"\xd0\x9f\xd1\x80\xd0\xb8"}\n\n'
        b'data: {"type":"token","delta":"\xd0\xb2\xd0\xb5\xd1\x82"}\n\n'
        b'data: {"type":"done"}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        # Тело — form-encoded (без media) или multipart (с media);
        # JSON-body здесь точно не должно быть.
        ct = request.headers["content-type"]
        assert ct.startswith("application/x-www-form-urlencoded") or ct.startswith(
            "multipart/form-data"
        )
        # Поле content передано в form-теле
        assert b"content=hi" in request.content or b"hi" in request.content
        return httpx.Response(
            200,
            content=sse_body,
            headers={"Content-Type": "text/event-stream"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://x") as c:
        client = BackendClient(c)
        events = [d async for d in client.send_message(uuid4(), "hi")]
    # Все events — dict-кадры (token), done выкинул из цикла
    assert all(isinstance(e, dict) for e in events)
    deltas = [e["delta"] for e in events if e.get("type") == "token"]
    assert "".join(deltas) == "Привет"


@pytest.mark.asyncio
async def test_send_message_yields_message_saved_event():
    """Backend сообщает id сохранённого ответа отдельным SSE-кадром."""
    sse_body = (
        b'data: {"type":"token","delta":"hi"}\n\n'
        b'data: {"type":"message_saved","message_id":"00000000-0000-0000-0000-000000000abc"}\n\n'
        b'data: {"type":"done"}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=sse_body,
            headers={"Content-Type": "text/event-stream"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://x") as c:
        client = BackendClient(c)
        events = [d async for d in client.send_message(uuid4(), "hi")]
    saved = [e for e in events if e.get("type") == "message_saved"]
    assert len(saved) == 1
    assert saved[0]["message_id"] == "00000000-0000-0000-0000-000000000abc"


@pytest.mark.asyncio
async def test_send_message_with_media_attaches_file():
    """С media-байтами клиент должен отправить multipart с media-частью."""
    sse_body = (
        b'data: {"type":"token","delta":"ok"}\n\n'
        b'data: {"type":"done"}\n\n'
    )
    captured_body: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_body["content_type"] = request.headers["content-type"]
        captured_body["body"] = request.content
        return httpx.Response(
            200,
            content=sse_body,
            headers={"Content-Type": "text/event-stream"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://x") as c:
        client = BackendClient(c)
        events = [
            d async for d in client.send_message(
                uuid4(),
                "describe",
                media=b"\xff\xd8\xff\xe0fake-jpeg",
                mime="image/jpeg",
                filename="photo.jpg",
            )
        ]

    deltas = [e["delta"] for e in events if e.get("type") == "token"]
    assert deltas == ["ok"]
    assert captured_body["content_type"].startswith("multipart/form-data")
    # multipart-тело должно содержать имя файла и текст
    body = captured_body["body"]
    assert b"photo.jpg" in body
    assert b"image/jpeg" in body
    assert b"describe" in body


@pytest.mark.asyncio
async def test_send_message_ignores_unknown_event_types():
    sse_body = (
        b'data: {"type":"ping"}\n\n'
        b'data: {"type":"token","delta":"hi"}\n\n'
        b'data: {"type":"done"}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse_body)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://x") as c:
        client = BackendClient(c)
        events = [d async for d in client.send_message(uuid4(), "hi")]
    deltas = [e["delta"] for e in events if e.get("type") == "token"]
    assert deltas == ["hi"]


@pytest.mark.asyncio
async def test_send_message_skips_lines_without_data_prefix():
    sse_body = (
        b": keepalive\n\n"
        b'data: {"type":"token","delta":"x"}\n\n'
        b'data: {"type":"done"}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse_body)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://x") as c:
        client = BackendClient(c)
        events = [d async for d in client.send_message(uuid4(), "hi")]
    deltas = [e["delta"] for e in events if e.get("type") == "token"]
    assert deltas == ["x"]


@pytest.mark.asyncio
async def test_clear_messages_sends_delete():
    chat_id = uuid4()
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(204)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://x") as c:
        client = BackendClient(c)
        await client.clear_messages(chat_id)
    assert seen["method"] == "DELETE"
    assert seen["path"] == f"/chats/{chat_id}/messages"


@pytest.mark.asyncio
async def test_get_or_create_chat_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://x") as c:
        client = BackendClient(c)
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_or_create_chat("tg-1", "telegram")


@pytest.mark.asyncio
async def test_broadcast_sends_admin_token_and_interface():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["admin_token"] = request.headers.get("X-Admin-Token")
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"sent": 5, "failed": 1})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://x") as c:
        client = BackendClient(c, admin_token="secret-token")
        result = await client.broadcast("Тех-работы в 02:00", interface="telegram")

    assert seen["method"] == "POST"
    assert seen["path"] == "/chats/admin/broadcast"
    assert seen["admin_token"] == "secret-token"
    assert seen["body"] == {"text": "Тех-работы в 02:00", "interface": "telegram"}
    assert result == {"sent": 5, "failed": 1}
