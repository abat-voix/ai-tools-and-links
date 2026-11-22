import asyncio
from collections.abc import AsyncIterator
from typing import Literal, cast

from openai import AsyncOpenAI
from openai.types.responses import ResponseInputItemParam, ResponseInputParam
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.exceptions import IncompleteResponseError
from app.schemas.chat import ChatRequest, ChatResponse, Usage
from app.services.tools import TOOLS, execute_tool

CHAT_INSTRUCTIONS = "Помогай пользователям SaaS. Уточняй недостающие данные. Не выдумывай статусы заявок."
INSTRUCTIONS = (
    CHAT_INSTRUCTIONS + " Проверяй статус через инструмент. Если заявка недоступна, сообщи об этом."
)


class LLMService:
    def __init__(self, client: AsyncOpenAI, cache: Redis | None, settings: Settings) -> None:
        self.client = client
        self.cache = cache
        self.settings = settings

    async def complete(self, request: ChatRequest, user_id: str) -> ChatResponse:
        history: ResponseInputParam = [
            {"role": message.role, "content": message.content} for message in request.messages
        ]
        totals = Usage()
        async with asyncio.timeout(self.settings.request_timeout):
            for _ in range(4):
                response = await self.client.responses.create(
                    model=self.settings.openai_model,
                    instructions=INSTRUCTIONS,
                    input=history,
                    tools=TOOLS,
                    parallel_tool_calls=False,
                    include=["reasoning.encrypted_content"],
                    store=False,
                    max_output_tokens=1024,
                )
                if response.status != "completed":
                    raise IncompleteResponseError
                usage = Usage.from_response(response.usage)
                totals.input_tokens += usage.input_tokens
                totals.output_tokens += usage.output_tokens
                totals.total_tokens += usage.total_tokens
                totals.cached_tokens += usage.cached_tokens

                calls = [item for item in response.output if item.type == "function_call"]
                if not calls:
                    if not response.output_text:
                        raise IncompleteResponseError
                    return ChatResponse(content=response.output_text, model=response.model, usage=totals)

                history.extend(
                    cast(ResponseInputItemParam, item.model_dump(mode="json", exclude_none=True))
                    for item in response.output
                )
                history.extend(execute_tool(call, user_id) for call in calls)
        raise IncompleteResponseError

    async def stream(
        self, request: ChatRequest
    ) -> AsyncIterator[tuple[Literal["delta", "usage"], str]]:
        history: ResponseInputParam = [
            {"role": message.role, "content": message.content} for message in request.messages
        ]
        async with self.client.responses.stream(
            model=self.settings.openai_model,
            instructions=CHAT_INSTRUCTIONS,
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
