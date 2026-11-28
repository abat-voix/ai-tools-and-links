import json

import httpx
import pytest
from openai import AsyncOpenAI

from tests.response_fixtures import sse_body, terminal_event, text_delta


async def test_chat_creation_preserves_initial_prompt(chat_client):
    client, _ = chat_client
    payload = {"owner_external_id": "prompt-owner", "interface": "cli",
               "system_prompt": "Use only the supplied knowledge base."}
    created = await client.post("/chats", json=payload)
    assert created.status_code == 200
    chat_id = created.json()["chat_id"]
    stored = await client.get(f"/chats/{chat_id}")
    assert stored.json()["system_prompt"] == payload["system_prompt"]

    payload["system_prompt"] = "Replacement must not override the existing chat."
    repeated = await client.post("/chats", json=payload)
    assert repeated.json()["chat_id"] == chat_id
    stored = await client.get(f"/chats/{chat_id}")
    assert stored.json()["system_prompt"] == "Use only the supplied knowledge base."


@pytest.mark.parametrize("finish_reason", ["content_filter", "max_output_tokens", "failed", None, "empty"])
async def test_failed_stream_has_error_without_saved_answer_or_success(chat_client, finish_reason):
    client, service = chat_client

    async def handler(request):
        assert request.url.path == "/v1/responses"
        frames = [] if finish_reason == "empty" else [text_delta("partial")]
        if finish_reason == "failed":
            frames.append(terminal_event("failed"))
        elif finish_reason in {"content_filter", "max_output_tokens"}:
            frames.append(terminal_event("incomplete", reason=finish_reason))
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, text=sse_body(*frames),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with AsyncOpenAI(api_key="test-key", http_client=http) as llm:
            service.llm_client = llm
            created = await client.post("/chats", json={
                "owner_external_id": "failed-stream", "interface": "cli"})
            chat_id = created.json()["chat_id"]
            response = await client.post(f"/chats/{chat_id}/messages", data={"content": "hi"})
    events = [json.loads(line[6:]) for line in response.text.splitlines()
              if line.startswith("data: ")]
    assert any(event["type"] == "error" for event in events)
    assert all(event["type"] not in {"done", "message_saved"} for event in events)
    history = await client.get(f"/chats/{chat_id}/messages")
    assert [message["role"] for message in history.json()] == ["user"]


async def test_openai_gets_photo_and_caption_from_saved_history(chat_client):
    client, service = chat_client
    requests = []

    def upstream(request):
        assert request.url.path == "/v1/responses"
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=sse_body(text_delta("Фото получено"), terminal_event()),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
        async with AsyncOpenAI(api_key="test-key", http_client=http) as llm:
            service.llm_client = llm
            created = await client.post("/chats", json={
                "owner_external_id": "photo-user", "interface": "cli",
            })
            route = f"/chats/{created.json()['chat_id']}/messages"
            response = await client.post(route, data={"content": "Что видно?"},
                                         files={"media": ("photo.png", b"x", "image/png")})
            assert '"type": "message_saved"' in response.text
            await client.post(route, data={"content": "Какого цвета наклейка?"})

    first_input = requests[0]["input"][0]
    assert first_input == {
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Что видно?"},
            {"type": "input_image", "image_url": "data:image/png;base64,eA==",
             "detail": "auto"},
        ],
    }
    assert requests[1]["input"][0] == first_input
    assert requests[1]["input"][-1]["content"] == "Какого цвета наклейка?"
