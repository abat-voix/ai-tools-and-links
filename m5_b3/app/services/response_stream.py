"""Переход от событий Responses API к текстовым фрагментам сервиса."""

from collections.abc import AsyncGenerator

from app.core.exceptions import LLMContentFilterError, LLMError
from app.schemas.chat import ChatDelta, Usage


async def response_text_stream(stream) -> AsyncGenerator[ChatDelta]:
    has_text = False
    async with stream:
        async for event in stream:
            if event.type == "response.output_text.delta" and event.delta:
                has_text = has_text or bool(event.delta.strip())
                yield ChatDelta(content=event.delta)
            elif event.type == "response.completed" and has_text:
                if event.response.usage is not None:
                    yield ChatDelta(usage=Usage.from_openai(event.response.usage))
                return
            elif event.type == "response.incomplete":
                if event.response.incomplete_details and (
                    event.response.incomplete_details.reason == "content_filter"
                ):
                    raise LLMContentFilterError("Ответ заблокирован поставщиком модели")
                break
            elif event.type in {"response.failed", "error"}:
                break
    raise LLMError("Модель не вернула завершённый текстовый ответ")
