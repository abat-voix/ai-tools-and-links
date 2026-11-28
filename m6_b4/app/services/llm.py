import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import aclosing

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import (
    LLMAuthError,
    LLMContentFilterError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from app.schemas.chat import ChatDelta, ChatRequest, ChatResponse
from app.services.request_options import response_options
from app.services.response_stream import response_text_stream


class LLMService:
    def __init__(self, llm, cache, ttl: int = 3600):
        self.llm = llm
        self.cache = cache
        self.ttl = ttl

    def _key(self, req: ChatRequest) -> str:
        payload = req.model_dump(exclude={"user_id", "stream"})
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return "chat:responses:" + hashlib.sha256(blob.encode()).hexdigest()

    @staticmethod
    def _response_input(req: ChatRequest) -> list[dict[str, str]]:
        messages = []
        for message in req.messages:
            if message.role == "tool":
                # Публичный /chat принимает только текст без call_id.
                messages.append({
                    "role": "user",
                    "content": f"Результат инструмента:\n{message.content}",
                })
            else:
                messages.append(message.model_dump())
        return messages

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _call(self, req: ChatRequest) -> ChatResponse:
        try:
            raw = await self.llm.responses.create(
                model=req.model,
                input=self._response_input(req),
                store=False,
                **response_options(req.model, req.max_tokens, req.temperature),
            )
            if raw.status not in {"completed", "incomplete"}:
                raise LLMError("Модель не вернула ответ")
            return ChatResponse.from_openai(raw)
        except RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except AuthenticationError as e:
            raise LLMAuthError(str(e)) from e
        except APITimeoutError as e:
            raise LLMTimeoutError(str(e)) from e
        except BadRequestError as e:
            msg = str(e).lower()
            if "content" in msg and ("filter" in msg or "policy" in msg):
                raise LLMContentFilterError(str(e)) from e
            raise LLMError(str(e)) from e
        except APIConnectionError as e:
            raise LLMError(f"connection error: {e}") from e

    async def complete(self, req: ChatRequest) -> ChatResponse:
        # Нулевая температура — политика кеширования, не гарантия детерминизма.
        if req.temperature > 0 or self.cache is None:
            resp = await self._call(req)
            resp.cached = False
            return resp

        key = self._key(req)
        blob = await self.cache.get(key)
        if blob:
            resp = ChatResponse.model_validate_json(blob)
            resp.cached = True
            return resp

        resp = await self._call(req)
        resp.cached = False
        await self.cache.setex(key, self.ttl, resp.model_dump_json())
        return resp

    async def stream(self, req: ChatRequest) -> AsyncIterator[ChatDelta]:
        stream = await self.llm.responses.create(
            model=req.model,
            input=self._response_input(req),
            store=False,
            **response_options(req.model, req.max_tokens, req.temperature),
            stream=True,
        )
        async with aclosing(response_text_stream(stream)) as deltas:
            async for delta in deltas:
                yield delta
