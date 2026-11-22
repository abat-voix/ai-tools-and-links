import json

import pytest
from conftest import reply_body

from app.services.tickets import get_ticket_status

REQUEST = {"messages": [{"role": "user", "content": "Какой статус заявки T-1042?"}]}


def call(ticket: str, *, call_id: str = "call_ticket", arguments: dict | None = None) -> dict:
    return {
        "id": "fc_item",
        "type": "function_call",
        "status": "completed",
        "name": "get_ticket_status",
        "arguments": json.dumps(arguments if arguments is not None else {"ticket_id": ticket}),
        "call_id": call_id,
    }


@pytest.mark.parametrize(
    ("ticket", "arguments", "expected"),
    [
        ("T-1042", None, {"status": "in_progress"}),
        ("T-2042", None, {"error": "not_found"}),
        ("T-0000", None, {"error": "not_found"}),
        ("T-2042", {"ticket_id": "T-2042", "user_id": "support-b"}, {"error": "invalid_arguments"}),
    ],
)
async def test_tool_loop_and_permissions(client, session, ticket, arguments, expected):
    session["replies"] += [reply_body([call(ticket, arguments=arguments)]), reply_body()]
    result = await client.post("/chat", json=REQUEST)
    assert result.status_code == 200
    first, second = (json.loads(req.content) for req in session["requests"])
    assert first["tools"][0]["strict"] is True
    assert first["include"] == ["reasoning.encrypted_content"]
    assert first["store"] is False
    assert "previous_response_id" not in second
    assert second["input"][-2]["id"] == "fc_item"
    assert second["input"][-1]["type"] == "function_call_output"
    assert second["input"][-1]["call_id"] == "call_ticket"
    assert json.loads(second["input"][-1]["output"]) == expected
    assert result.json()["usage"]["total_tokens"] == 30


async def test_tool_loop_is_bounded(client, session):
    session["replies"] += [reply_body([call("T-1042", call_id=f"call_{i}")]) for i in range(4)]
    response = await client.post("/chat", json=REQUEST)
    assert response.status_code == 502
    assert len(session["requests"]) == 4


def test_ticket_lookup_by_owner():
    assert get_ticket_status("support-a", "T-1042") == "in_progress"
    assert get_ticket_status("support-a", "T-1043") == "resolved"
    assert get_ticket_status("support-b", "T-2042") == "resolved"
    assert get_ticket_status("support-b", "T-1042") is None
