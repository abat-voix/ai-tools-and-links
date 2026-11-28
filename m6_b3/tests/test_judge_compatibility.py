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


async def test_sonnet_judge_omits_sampling_and_forced_tool_choice(monkeypatch):
    from anthropic import AsyncAnthropic

    requests = []

    async def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        content = [{'type':'text','text':'{"has_citation":"yes"}'}]
        if body.get('tools'):
            content = [{'type':'tool_use','id':'t1','name':body['tools'][0]['name'],
                        'input':{'has_citation':'yes'}}]
        return httpx.Response(200, json={
            'id':'msg_test','type':'message','role':'assistant',
            'model':'claude-sonnet-5-5','content':content,
            'stop_reason':'tool_use' if body.get('tools') else 'end_turn',
            'stop_sequence':None,'usage':{'input_tokens':1,'output_tokens':1},
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with AsyncAnthropic(api_key='test-key', http_client=http) as api:
            monkeypatch.setattr(metrics, 'AsyncAnthropic', lambda **_: api)
            judge, _ = metrics.build_judge(Settings(
                _env_file=None, llm={'openai_api_key':'test-key'},
                anthropic_api_key='test-key',
            ))
            verdict = await judge.agenerate('Есть ли цитата [1]?', metrics.CitationVerdict)
    assert verdict.has_citation == 'yes'
    for field in ('temperature','top_p','top_k','tool_choice'):
        assert field not in requests[0]


def test_testset_llm_accepts_current_sonnet():
    from scripts.generate_testset import build_generator_llm

    llm = build_generator_llm(Settings(
        _env_file=None, llm={'openai_api_key':'test-key'},
        anthropic_api_key='test-key',
    ))
    assert llm.metadata.context_window == 1_000_000
    assert 'temperature' not in llm._model_kwargs
