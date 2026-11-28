import json

import httpx
import pytest

from app.agents.model import build_agent_model
from app.agents.tools import multiply
from app.core.config import Settings


@pytest.mark.parametrize("model,effort", [
    ("gpt-6-luna", "none"),
    ("gpt-6.2-sol", "low"),
    ("gpt-6.2-astra", "low"),
])
async def test_agent_model_wire_tool_call(model, effort):
    requests = []

    async def handler(request):
        requests.append((request.url.path, json.loads(request.content)))
        call = {"name":"multiply", "arguments":'{"a":2,"b":3}'}
        payload = {"id":"r1", "object":"response", "created_at":1,
            "status":"completed", "model":model, "output":[{
                "type":"function_call", "id":"f1", "call_id":"c1", **call,
                "status":"completed"}],
            "usage":{"input_tokens":3,"output_tokens":1,"total_tokens":4}}
        return httpx.Response(200, json=payload)

    settings = Settings(_env_file=None, llm={"openai_api_key":"test-key", "default_model":model})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        llm = build_agent_model(settings, http_async_client=http)
        response = await llm.bind_tools([multiply]).ainvoke("2 * 3")
    assert response.tool_calls[0]["args"] == {"a":2,"b":3}
    path, body = requests[0]
    assert path.endswith("/responses")
    assert body["reasoning"]["effort"] == effort
    if effort != "none":
        assert "temperature" not in body


@pytest.mark.parametrize("metadata,content", [
    ({"status":"incomplete", "incomplete_details":{"reason":"max_output_tokens"}}, "Partial"),
    ({"finish_reason":"length"}, "Partial"),
    ({"finish_reason":"content_filter"}, "Blocked"),
    ({"status":"completed"}, [{"type":"reasoning", "summary":[]}]),
])
@pytest.mark.parametrize("persistent", [False])
async def test_graph_rejects_unsuccessful_model_response(metadata, content, persistent):
    from langchain_core.messages import AIMessage, HumanMessage
    from app.agents.graph import build_custom_graph

    class Model:
        def bind_tools(self, tools):
            return self
        async def ainvoke(self, messages):
            return AIMessage(content=content, response_metadata=metadata)

    initial = {"messages":[HumanMessage("question")], "iteration_count":0,
               "tool_results":[], "draft":None, "sent":False}
    if persistent:
        try:
            from app.services.agent_persistent import build_agent
        except ImportError:
            pytest.skip("No persistent graph in this block")
        from langgraph.checkpoint.memory import InMemorySaver
        from unittest.mock import AsyncMock
        graph = build_agent(InMemorySaver(), Model(), [], AsyncMock())
    else:
        graph = build_custom_graph(Model(), [])
    with pytest.raises(ValueError, match="LLM"):
        await graph.ainvoke(initial, {"configurable":{"thread_id":"bad-response"}})
