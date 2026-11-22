import json

import httpx
import pytest
from openai import OpenAI

from app.services.agent_naive import run_agent


def test_luna_sends_supported_tool_request():
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            'id':'x', 'object':'chat.completion','created':1,'model':'gpt-6-luna',
            'choices':[{'index':0,'message':{'role':'assistant','content':'Готово'},
                        'finish_reason':'stop'}],
        })
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with OpenAI(api_key='test-key', http_client=http) as client:
            result = run_agent('Привет', client=client)
    assert result['answer'] == 'Готово'
    assert requests[0]['model'] == 'gpt-6-luna'
    assert requests[0]['reasoning_effort'] == 'none'


@pytest.mark.parametrize('finish,content', [('length','обрыв'),('content_filter',''),('stop','')])
def test_incomplete_reply_is_not_success(finish, content):
    def handler(request):
        return httpx.Response(200,json={
            'id':'x','object':'chat.completion','created':1,'model':'gpt-6-luna',
            'choices':[{'index':0,'message':{'role':'assistant','content':content},
                        'finish_reason':finish}],
        })
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with OpenAI(api_key='test-key', http_client=http) as client:
            result = run_agent('Привет', client=client)
    assert result.get('error')
    assert result['answer'] is None
