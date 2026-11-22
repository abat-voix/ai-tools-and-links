import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.schemas.chat import ChatRequest
from app.services.llm import LLMService
from app.core.exceptions import LLMError


@pytest.mark.parametrize("streaming", [False, True])
async def test_luna_request_uses_supported_reasoning_and_token_limit(streaming):
    """Both paths must send the public token budget using the current API field."""
    requests = []

    async def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        if body.get("stream"):
            chunk = {
                "id": "chatcmpl-test", "object": "chat.completion.chunk",
                "created": 0, "model": "gpt-6-luna",
                "choices": [{"index": 0, "delta": {"content": "answer"},
                             "finish_reason": "stop"}],
            }
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"},
                text=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n",
            )
        return httpx.Response(200, json={
            "id": "chatcmpl-test", "object": "chat.completion", "created": 0,
            "model": "gpt-6-luna",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "answer"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with AsyncOpenAI(api_key="test-key", http_client=http) as llm:
            service = LLMService(llm, cache=None)
            request = ChatRequest(
                model="gpt-6-luna", messages=[{"role": "user", "content": "question"}],
                max_tokens=321, temperature=0,
            )
            if streaming:
                deltas = [delta async for delta in service.stream(request)]
                assert "".join(delta.content or "" for delta in deltas) == "answer"
            else:
                assert (await service.complete(request)).content == "answer"

    assert len(requests) == 1
    assert requests[0]["max_completion_tokens"] == 321
    assert requests[0]["reasoning_effort"] == "none"
    assert "max_tokens" not in requests[0]


@pytest.mark.parametrize("reason", ["content_filter", "length", None])
async def test_stateless_stream_rejects_unsuccessful_termination(reason):
    chunk = {"id": "c-test", "object": "chat.completion.chunk", "created": 0,
             "model": "gpt-6-luna", "choices": [{"index": 0,
             "delta": {"content": "partial"}, "finish_reason": reason}]}
    transport = httpx.MockTransport(lambda _: httpx.Response(
        200, headers={"content-type": "text/event-stream"},
        text=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n",
    ))
    async with httpx.AsyncClient(transport=transport) as http:
        async with AsyncOpenAI(api_key="test-key", http_client=http) as llm:
            service = LLMService(llm, cache=None)
            request = ChatRequest(messages=[{"role": "user", "content": "hello"}])
            with pytest.raises(LLMError):
                [delta async for delta in service.stream(request)]
