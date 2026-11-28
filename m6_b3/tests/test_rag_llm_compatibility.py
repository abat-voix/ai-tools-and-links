import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from llama_index.core import Settings as LlamaSettings
from openai import AsyncOpenAI, OpenAI

from app.core.config import Settings
from app.services import rag as rag_module
from app.services.rag_baremetal import BareMetalRAG


def _response(model: str) -> httpx.Response:
    return httpx.Response(200, json={
        "id": "resp-test", "object": "response", "created_at": 0,
        "model": model, "status": "completed",
        "output": [{"id": "msg-test", "type": "message", "role": "assistant",
                    "status": "completed", "content": [{
                        "type": "output_text", "text": "answer", "annotations": [],
                    }]}],
    })


@pytest.mark.parametrize("model,effort", [("gpt-6-luna", "none"), ("gpt-6.2-sol", "low")])
async def test_rag_llm_sends_model_compatible_responses_request(monkeypatch, model, effort):
    monkeypatch.setattr(rag_module, "QdrantClient", lambda **_: SimpleNamespace())
    monkeypatch.setattr(rag_module, "AsyncQdrantClient", lambda **_: SimpleNamespace())
    requests = []

    async def handler(request):
        assert request.url.path == "/v1/responses"
        requests.append(json.loads(request.content))
        return _response(model)

    previous_llm = LlamaSettings._llm
    try:
        rag_module.RAGService(Settings(
            _env_file=None, llm={"openai_api_key": "test-key"}, rag_llm_model=model,
        ))
        llm = LlamaSettings.llm
        llm.max_retries = 0
        assert llm.metadata.context_window == 1_050_000
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with AsyncOpenAI(api_key="test-key", http_client=http, max_retries=0) as api:
                llm._aclient = api
                result = await llm.acomplete("question")
        assert result.text == "answer"
        assert requests[0]["reasoning"] == {"effort": effort}
        assert requests[0]["store"] is False
        assert "messages" not in requests[0]
        assert "max_tokens" not in requests[0]
        if effort == "none":
            assert requests[0]["temperature"] == 0.0
        else:
            assert "temperature" not in requests[0]
            assert "top_p" not in requests[0]
    finally:
        LlamaSettings._llm = previous_llm


@pytest.mark.parametrize("model,effort", [("gpt-6-luna", "none"), ("gpt-6.2-sol", "low")])
def test_baremetal_rag_sends_context_to_responses_and_keeps_source(model, effort):
    service = BareMetalRAG.__new__(BareMetalRAG)
    service._settings = Settings(_env_file=None, rag_llm_model=model)
    service._collection = "test"
    service._embed = Mock(return_value=[[0.1]])
    service._client = Mock()
    service._client.query_points.return_value.points = [SimpleNamespace(
        score=0.9, payload={"source": "policy.md", "text": "Refund policy."},
    )]
    requests = []

    def handler(request):
        assert request.url.path == "/v1/responses"
        requests.append(json.loads(request.content))
        return _response(model)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with OpenAI(api_key="test-key", http_client=http, max_retries=0) as api:
            service._openai = api
            result = service.answer("question")

    assert result == {
        "answer": "answer", "top_score": 0.9,
        "sources": [{"source": "policy.md", "text": "Refund policy.", "score": 0.9}],
    }
    assert "[policy.md] Refund policy." in requests[0]["input"][1]["content"]
    assert requests[0]["reasoning"] == {"effort": effort}
    assert requests[0]["store"] is False
    if effort != "none":
        assert "temperature" not in requests[0]
