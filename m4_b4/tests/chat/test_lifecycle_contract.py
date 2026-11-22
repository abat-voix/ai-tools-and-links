import json

import httpx
import pytest
from openai import AsyncOpenAI


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


@pytest.mark.parametrize("finish_reason", ["content_filter", "length", None, "empty"])
async def test_failed_stream_has_error_without_saved_answer_or_success(chat_client, finish_reason):
    client, service = chat_client

    async def handler(request):
        choices = [{"index": 0, "delta": {"content": "partial"},
                    "finish_reason": None}]
        first = {"id": "c-test", "object": "chat.completion.chunk", "created": 0,
                 "model": "gpt-6-luna", "choices": choices}
        frames = [] if finish_reason == "empty" else [first]
        if finish_reason in {"content_filter", "length"}:
            frames.append({**first, "choices": [{"index": 0, "delta": {},
                                               "finish_reason": finish_reason}]})
        body = "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames)
        return httpx.Response(200, headers={"content-type": "text/event-stream"},
                              text=body + "data: [DONE]\n\n")

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
