import json
from types import SimpleNamespace

import httpx
import pytest
from llama_index.core import Settings as LlamaSettings
from openai import AsyncOpenAI

from app.core.config import Settings
from app.services import rag as rag_module


@pytest.mark.parametrize("model,effort", [("gpt-6-luna", "none"), ("gpt-6.1-sol", "low")])
async def test_current_model_has_metadata_and_sends_supported_request(monkeypatch, model, effort):
    monkeypatch.setattr(rag_module, "QdrantClient", lambda **_: SimpleNamespace())
    monkeypatch.setattr(rag_module, "AsyncQdrantClient", lambda **_: SimpleNamespace())
    requests = []

    async def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "c-test", "object": "chat.completion", "created": 0,
            "model": "gpt-6-luna", "choices": [{"index": 0,
            "message": {"role": "assistant", "content": "answer"},
            "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
        })

    previous_llm = LlamaSettings._llm
    try:
        rag_module.RAGService(Settings(
            _env_file=None, llm={"openai_api_key": "test-key"}, rag_llm_model=model,
        ))
        llm = LlamaSettings.llm
        assert llm.metadata.context_window == 1_050_000
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async with AsyncOpenAI(api_key="test-key", http_client=http) as api:
                llm._aclient = api
                result = await llm.acomplete("question")
        assert result.text == "answer"
        assert requests[0]["reasoning_effort"] == effort
        assert "max_tokens" not in requests[0]
        if effort != "none":
            assert "temperature" not in requests[0]
    finally:
        LlamaSettings._llm = previous_llm


@pytest.mark.parametrize("model,effort", [("gpt-6-luna", "none"), ("gpt-6.1-sol", "low")])
def test_baremetal_rag_uses_model_compatible_options(model, effort):
    from unittest.mock import Mock
    from app.services.rag_baremetal import BareMetalRAG
    service = BareMetalRAG.__new__(BareMetalRAG)
    service._settings = Settings(_env_file=None, rag_llm_model=model)
    service._collection = "test"
    service._embed = Mock(return_value=[[0.1]])
    service._client = Mock()
    service._client.query_points.return_value.points = []
    service._openai = Mock()
    service._openai.chat.completions.create.return_value.choices = [
        SimpleNamespace(message=SimpleNamespace(content="answer"))
    ]
    service.answer("question")
    kwargs = service._openai.chat.completions.create.call_args.kwargs
    assert kwargs["reasoning_effort"] == effort
    if effort != "none":
        assert "temperature" not in kwargs
