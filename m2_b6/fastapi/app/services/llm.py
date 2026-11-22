import hashlib
import logging
from collections.abc import AsyncIterator
from typing import Literal

from openai import AsyncOpenAI
from openai.types.responses import ResponseInputParam
from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings
from app.core.exceptions import IncompleteResponseError
from app.schemas.chat import ChatRequest, ChatResponse, Usage

logger = logging.getLogger(__name__)

INSTRUCTIONS = "Помогай пользователям SaaS. Уточняй недостающие данные. Не выдумывай статусы заявок."


class LLMService:
    def __init__(self, client: AsyncOpenAI, cache: Redis | None, settings: Settings) -> None:
        self.client = client
        self.cache = cache
        self.settings = settings

    def _cache_key(self, request: ChatRequest, user_id: str) -> str:
        payload = "\n".join((user_id, self.settings.openai_model, INSTRUCTIONS, request.model_dump_json()))
        return "support:" + hashlib.sha256(payload.encode()).hexdigest()

    async def complete(self, request: ChatRequest, user_id: str) -> ChatResponse:
        cache = self.cache if request.cache else None
        key = self._cache_key(request, user_id)
        if cache is not None:
            try:
                if blob := await cache.get(key):
                    return ChatResponse.model_validate_json(blob).model_copy(update={"cached": True, "usage": Usage()})
            except (RedisError, ValidationError):
                logger.info("Ответ из кеша недоступен")

        history: ResponseInputParam = [
            {"role": message.role, "content": message.content} for message in request.messages
        ]
        response = await self.client.responses.create(
            model=self.settings.openai_model,
            instructions=INSTRUCTIONS,
            input=history,
            store=False,
            max_output_tokens=1024,
        )
        if response.status != "completed" or not response.output_text:
            raise IncompleteResponseError

        result = ChatResponse(
            content=response.output_text,
            model=response.model,
            usage=Usage.from_response(response.usage),
        )
        if cache is not None and result.content:
            try:
                await cache.set(key, result.model_dump_json(), ex=self.settings.cache_ttl_seconds)
            except RedisError:
                logger.info("Кеш недоступен для записи")
        return result

    async def stream(
        self, request: ChatRequest
    ) -> AsyncIterator[tuple[Literal["delta", "usage"], str]]:
        history: ResponseInputParam = [
            {"role": message.role, "content": message.content} for message in request.messages
        ]
        async with self.client.responses.stream(
            model=self.settings.openai_model,
            instructions=INSTRUCTIONS,
            input=history,
            store=False,
            max_output_tokens=1024,
        ) as stream:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    yield "delta", event.delta
            response = await stream.get_final_response()
            if response.status != "completed" or not response.output_text:
                raise IncompleteResponseError
            yield "usage", Usage.from_response(response.usage).model_dump_json()
