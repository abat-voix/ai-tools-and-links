from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram.enums import ChatType

from bot.services.streaming import stream_to_chat


@pytest.mark.parametrize("chat_type", [ChatType.PRIVATE, ChatType.GROUP])
async def test_long_stream_finishes_as_file_with_feedback(chat_type):
    bot = SimpleNamespace(
        send_message=AsyncMock(), send_message_draft=AsyncMock(), send_document=AsyncMock(),
    )
    sent = SimpleNamespace(edit_text=AsyncMock())
    message = SimpleNamespace(
        bot=bot, chat=SimpleNamespace(id=42, type=chat_type), answer=AsyncMock(return_value=sent),
    )
    text = "Длинный ответ.\n" * 400
    message_id = str(uuid4())

    async def events():
        yield {"type": "token", "delta": text}
        yield {"type": "message_saved", "message_id": message_id}

    assert await stream_to_chat(message, events(), chat_id=uuid4()) == text
    bot.send_message.assert_not_awaited()
    bot.send_document.assert_awaited_once()
    arguments = bot.send_document.await_args.kwargs
    assert arguments["document"].filename == "answer.txt"
    assert arguments["document"].data == text.encode("utf-8")
    assert all(message_id in button.callback_data for row in arguments["reply_markup"].inline_keyboard
               for button in row)
    if chat_type == ChatType.PRIVATE:
        bot.send_message_draft.assert_awaited_once()
    else:
        bot.send_message_draft.assert_not_awaited()
        message.answer.assert_awaited_once_with("…")
