"""Actual RAGAS + OpenAI SDK transport; no paid API requests."""
import json

import httpx
import pytest

pytest.importorskip('ragas')

from app.core.config import Settings  # noqa: E402
from app.eval import metrics  # noqa: E402


@pytest.mark.parametrize('model,effort', [('gpt-6-luna','none'), ('gpt-6.1-sol','low')])
async def test_judge_uses_model_specific_api_parameters(monkeypatch, model, effort):
    requests = []

    async def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            'id':'judge-test', 'object':'chat.completion', 'created':0, 'model':model,
            'choices':[{'index':0,'message':{'role':'assistant',
                'content':'{"has_citation":"yes"}'},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2},
        })

    actual_client = metrics.AsyncOpenAI
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with actual_client(api_key='test-key', http_client=http) as api:
            monkeypatch.setattr(metrics, 'AsyncOpenAI', lambda **_: api)
            judge, _ = metrics.build_judge(Settings(
                _env_file=None, llm={'openai_api_key':'test-key'},
                eval_judge_provider='openai', eval_judge_model=model,
            ))
            result = await judge.agenerate('Есть ли цитата [1]?', metrics.CitationVerdict)
    assert result.has_citation == 'yes'
    assert requests[0]['reasoning_effort'] == effort
    assert 'max_tokens' not in requests[0]
    if effort != 'none':
        assert 'temperature' not in requests[0]
        assert 'top_p' not in requests[0]


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
