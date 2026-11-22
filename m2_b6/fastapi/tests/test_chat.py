import json

import httpx
from conftest import reply_body

REQUEST = {"messages": [{"role": "user", "content": "Как восстановить пароль?"}]}


async def test_chat_uses_responses(client, session):
    response = await client.post("/chat", json=REQUEST)
    assert response.status_code == 200
    assert response.json()["content"] == "Принято"
    assert response.json()["usage"]["cached_tokens"] == 2
    assert session["requests"][0].url.path == "/v1/responses"
    args = json.loads(session["requests"][0].content)
    assert args["input"] == REQUEST["messages"]
    assert args["store"] is False
    assert response.headers["x-request-id"]


async def test_bad_role_never_reaches_model(client, session):
    result = await client.post("/chat", json={"messages": [{"role": "developer", "content": "x"}]})
    assert result.status_code == 422
    assert session["requests"] == []


async def test_bad_token_never_reaches_model(client, session):
    result = await client.post("/chat", json=REQUEST, headers={"Authorization": "Bearer wrong"})
    assert result.status_code == 401
    assert session["requests"] == []


async def test_incomplete_and_provider_error_are_clean(client, session):
    session["replies"] += [
        reply_body(status="incomplete"),
        httpx.Response(400, json={"error": {"message": "private provider detail"}}),
    ]
    for _ in range(2):
        result = await client.post("/chat", json=REQUEST)
        assert result.status_code == 502
        assert result.json() == {"detail": "Модель сейчас не ответила"}


async def test_cache_keys_separate_users_and_hit_avoids_provider(client, session, cache):
    body = REQUEST | {"cache": True}
    first = await client.post("/chat", json=body)
    key_a = cache.get.await_args.args[0]
    assert first.status_code == 200

    await client.post("/chat", json=body, headers={"Authorization": "Bearer test-profile-b"})
    key_b = cache.get.await_args.args[0]
    assert key_a != key_b

    cache.get.return_value = first.text
    repeated = await client.post("/chat", json=body)
    assert repeated.json()["cached"] is True
    assert repeated.json()["usage"]["total_tokens"] == 0
    assert len(session["requests"]) == 2


async def test_sse_maps_responses_events(client, session):
    payload = reply_body()
    wire = [
        {"type": "response.created", "response": payload, "sequence_number": 0},
        {"type": "response.output_item.added", "item": payload["output"][0], "output_index": 0, "sequence_number": 1},
        {"type": "response.output_text.delta", "delta": "Принято", "item_id": "msg_mock", "content_index": 0, "output_index": 0, "sequence_number": 2},
        {"type": "response.completed", "response": payload, "sequence_number": 3},
    ]
    session["replies"].append(httpx.Response(
        200, text="".join(f"data: {json.dumps(event)}\n\n" for event in wire),
        headers={"Content-Type": "text/event-stream"},
    ))
    result = await client.post("/chat/stream", json=REQUEST)
    assert result.status_code == 200
    assert result.headers["content-type"].startswith("text/event-stream")
    assert "event: delta" in result.text
    assert "event: usage" in result.text
    assert result.text.endswith("event: done\ndata: {}\n\n")


async def test_basic_health(client):
    assert (await client.get("/health")).json() == {"status": "ok"}
    assert (await client.get("/ready")).json() == {"status": "ready"}
