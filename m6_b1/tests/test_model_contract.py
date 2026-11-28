import json

import httpx
import pytest
from openai import OpenAI

from app.services.agent_naive import run_agent


def make_response(*items, status="completed", reason=None):
    return {
        "id": "resp_1",
        "object": "response",
        "created_at": 1,
        "model": "gpt-6-luna",
        "status": status,
        "incomplete_details": {"reason": reason} if reason else None,
        "output": list(items),
    }


def make_output_message(content):
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": content, "annotations": []}],
    }


def test_luna_sends_supported_tool_request():
    requests = []
    tool_item = {
        "type": "function_call",
        "id": "fc_1",
        "call_id": "call_1",
        "name": "search_knowledge_base",
        "arguments": '{"query":"возврат"}',
    }

    def handler(request):
        assert request.url.path == "/v1/responses"
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(200, json=make_response(tool_item))
        return httpx.Response(200, json=make_response(make_output_message("Готово")))

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with OpenAI(api_key="test-key", http_client=http) as client:
            result = run_agent("Когда можно вернуть товар?", client=client)
    assert result["answer"] == "Готово"
    assert requests[0]["model"] == "gpt-6-luna"
    assert requests[0]["reasoning"] == {"effort": "none"}
    assert requests[0]["store"] is False
    assert "reasoning.encrypted_content" in requests[0]["include"]
    assert requests[0]["tools"][0]["name"] == "search_knowledge_base"
    assert requests[1]["input"][-2]["id"] == "fc_1"
    returned = requests[1]["input"][-1]
    assert returned["type"] == "function_call_output"
    assert returned["call_id"] == "call_1"
    assert "14 дней" in returned["output"]


@pytest.mark.parametrize(
    "status,reason,text",
    [
        ("incomplete", "max_output_tokens", "обрыв"),
        ("incomplete", "content_filter", ""),
        ("completed", None, ""),
    ],
)
def test_incomplete_reply_is_not_success(status, reason, text):
    def handler(request):
        return httpx.Response(
            200,
            json=make_response(make_output_message(text), status=status, reason=reason),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with OpenAI(api_key="test-key", http_client=http) as client:
            result = run_agent("Привет", client=client)
    assert result["error"] == (reason or "empty_response")
    assert result["answer"] is None
