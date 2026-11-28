"""Actual RAGAS + OpenAI SDK transport; no paid API requests."""
import json

import httpx
import pytest

pytest.importorskip('ragas')

from app.core.config import Settings  # noqa: E402
from app.eval import metrics  # noqa: E402


@pytest.mark.parametrize(
    "model,effort",
    [("gpt-6-luna", "none"), ("gpt-6.2-sol", "low"), ("gpt-4.1-mini", None)],
)
async def test_judge_uses_responses_with_structured_output(
    monkeypatch: pytest.MonkeyPatch, model: str, effort: str | None,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/responses"
        payload = json.loads(request.content)
        assert payload["model"] == model
        assert payload["max_output_tokens"] == 4096
        assert payload["store"] is False
        assert "max_completion_tokens" not in payload
        if effort is None:
            assert "reasoning" not in payload
        else:
            assert payload["reasoning"] == {"effort": effort}
        if effort == "low":
            assert "temperature" not in payload
            assert "top_p" not in payload
        assert payload["input"][0]["role"] == "user"
        assert payload["tool_choice"] == {"type": "function", "name": "CitationVerdict"}
        return httpx.Response(200, json={
            "id": "resp_eval", "object": "response", "model": model,
            "created_at": 0, "status": "completed",
            "output": [{
                "type": "function_call", "id": "fc_eval", "call_id": "call_eval",
                "name": "CitationVerdict", "arguments": '{"has_citation":"yes"}',
                "status": "completed",
            }],
            "usage": {"input_tokens": 10, "output_tokens": 6, "total_tokens": 16},
        })

    actual_client = metrics.AsyncOpenAI
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with actual_client(api_key="test-key", http_client=http) as client:
            monkeypatch.setattr(metrics, "AsyncOpenAI", lambda **_: client)
            judge, _ = metrics.build_judge(Settings(
                _env_file=None, llm={"openai_api_key": "test-key"},
                eval_judge_provider="openai", eval_judge_model=model,
            ))
            result = await metrics.make_has_citation(judge).ascore(response="Согласно [1].")
            assert result.value == "yes"
