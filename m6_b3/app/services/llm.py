import hashlib
import json
from collections.abc import AsyncIterator

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

from app.schemas.chat import ChatDelta, ChatRequest, ChatResponse, Usage
from app.services.request_options import completion_options


class LLMService:
    def __init__(self, llm, cache, ttl: int = 3600):
        self.llm = llm
        self.cache = cache
        self.ttl = ttl

    def _key(self, req: ChatRequest) -> str:
        payload = req.model_dump(exclude={"user_id", "stream"})
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return "chat:" + hashlib.sha256(blob.encode()).hexdigest()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _call(self, req: ChatRequest) -> ChatResponse:
        try:
            raw = await self.llm.chat.completions.create(
                model=req.model,
                messages=[m.model_dump() for m in req.messages],
                **completion_options(req.model, req.max_tokens, req.temperature),
            )
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
        stream = await self.llm.chat.completions.create(
            model=req.model,
            messages=[m.model_dump() for m in req.messages],
            **completion_options(req.model, req.max_tokens, req.temperature),
            stream=True,
            stream_options={"include_usage": True},
        )
        finish_reason = None
        has_text = False
        async for chunk in stream:
            if getattr(chunk, "choices", None):
                choice = chunk.choices[0]
                reason = getattr(choice, "finish_reason", None)
                if isinstance(reason, str):
                    finish_reason = reason
                if finish_reason == "content_filter":
                    raise LLMContentFilterError("Ответ заблокирован поставщиком модели")
                delta = choice.delta
                if getattr(delta, "content", None):
                    has_text = True
                    yield ChatDelta(content=delta.content)
            if getattr(chunk, "usage", None):
                yield ChatDelta(usage=Usage.from_openai(chunk.usage))
        if finish_reason != "stop" or not has_text:
            raise LLMError("Модель не вернула завершённый текстовый ответ")
