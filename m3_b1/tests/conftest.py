from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from openai import AsyncOpenAI

from app.core.config import Settings, get_settings
from app.deps.providers import get_cache, get_llm
from app.main import app


@pytest.fixture
def session():
    return {"requests": [], "replies": []}


@pytest.fixture
def cache():
    instance = AsyncMock()
    instance.get.return_value = None
    return instance


@pytest.fixture
async def client(session, cache):
    def handle(request: httpx.Request) -> httpx.Response:
        session["requests"].append(request)
        if session["replies"]:
            reply = session["replies"].pop(0)
            return reply if isinstance(reply, httpx.Response) else httpx.Response(200, json=reply)
        return httpx.Response(200, json=reply_body())

    settings = Settings(
        openai_api_key="mock-only",
        demo_token_a="test-profile-a",
        demo_token_b="test-profile-b",
        _env_file=None,
    )
    async with AsyncOpenAI(
        api_key="mock-only", http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle))
    ) as llm:
        overrides: dict[Callable[..., Any], Callable[..., Any]] = {
            get_settings: lambda: settings,
            get_llm: lambda: llm,
            get_cache: lambda: cache,
        }
        app.dependency_overrides.update(overrides)
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://local",
                headers={"Authorization": "Bearer test-profile-a"},
            ) as http:
                yield http
        finally:
            app.dependency_overrides.clear()


def reply_body(output: list[dict] | None = None, *, status: str = "completed") -> dict:
    return {
        "id": "resp_mock",
        "object": "response",
        "created_at": 1,
        "model": "gpt-6.1-terra",
        "status": status,
        "output": output if output is not None else [{
            "id": "msg_mock",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": "Принято", "annotations": []}],
        }],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "input_tokens_details": {"cached_tokens": 2},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }
