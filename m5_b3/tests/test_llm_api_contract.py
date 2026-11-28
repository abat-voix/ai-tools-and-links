import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.schemas.chat import ChatRequest
from app.services.llm import LLMService
from app.core.exceptions import LLMError
from tests.response_fixtures import response_payload, sse_body, terminal_event, text_delta


@pytest.mark.parametrize("streaming", [False, True])
async def test_luna_request_uses_supported_reasoning_and_token_limit(streaming):
    """Both paths must send the public token budget using the current API field."""
    requests = []

    async def handler(request):
        assert request.url.path == "/v1/responses"
        body = json.loads(request.content)
        requests.append(body)
        if body.get("stream"):
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                text=sse_body(text_delta("answer"), terminal_event()),
            )
        return httpx.Response(200, json=response_payload())

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
    assert requests[0]["max_output_tokens"] == 321
    assert requests[0]["reasoning"] == {"effort": "none"}
    assert requests[0]["store"] is False
    assert requests[0]["input"] == [{"role": "user", "content": "question"}]
    assert "messages" not in requests[0]


@pytest.mark.parametrize("reason", ["content_filter", "max_output_tokens", None])
async def test_stateless_stream_rejects_unsuccessful_termination(reason):
    events = [text_delta("partial")]
    if reason:
        events.append(terminal_event("incomplete", reason=reason))
    transport = httpx.MockTransport(lambda _: httpx.Response(
        200,
        headers={"content-type": "text/event-stream"},
        text=sse_body(*events),
    ))
    async with httpx.AsyncClient(transport=transport) as http:
        async with AsyncOpenAI(api_key="test-key", http_client=http) as llm:
            service = LLMService(llm, cache=None)
            request = ChatRequest(messages=[{"role": "user", "content": "hello"}])
            with pytest.raises(LLMError):
                [delta async for delta in service.stream(request)]


async def test_sol_uses_reasoning_and_omits_temperature():
    def upstream(request):
        body = json.loads(request.content)
        assert body["model"] == "gpt-6.2-sol"
        assert body["reasoning"] == {"effort": "low"}
        assert "temperature" not in body
        return httpx.Response(200, json=response_payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
        async with AsyncOpenAI(api_key="test-key", http_client=http) as llm:
            service = LLMService(llm, cache=None)
            request = ChatRequest(
                model="gpt-6.2-sol", messages=[{"role": "user", "content": "question"}],
            )
            assert (await service.complete(request)).content == "answer"
