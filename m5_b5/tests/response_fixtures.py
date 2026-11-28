"""Моки текста и SSE для Responses API."""

import json
from types import SimpleNamespace


class MockTextStream:
    def __init__(self, *pieces: str):
        self.pieces = pieces

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        pass

    async def __aiter__(self):
        for piece in self.pieces:
            yield SimpleNamespace(type="response.output_text.delta", delta=piece)
        yield SimpleNamespace(
            type="response.completed",
            response=SimpleNamespace(usage=SimpleNamespace(
                input_tokens=5, output_tokens=3, total_tokens=8,
            )),
        )


def response_payload(status="completed", text="answer", reason=None):
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 0,
        "status": status,
        "model": "gpt-6-luna",
        "output": [{
            "type": "message", "id": "msg_test", "role": "assistant",
            "status": status,
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        }],
        "usage": {"input_tokens": 2, "output_tokens": 1, "total_tokens": 3},
        "incomplete_details": {"reason": reason} if reason else None,
    }


def sse_body(*events):
    return "".join(f"data: {json.dumps(event)}\n\n" for event in events)


def text_delta(text):
    return {
        "type": "response.output_text.delta", "delta": text, "item_id": "msg_test",
        "content_index": 0, "output_index": 0, "sequence_number": 0,
    }


def terminal_event(status="completed", reason=None):
    return {
        "type": f"response.{status}", "sequence_number": 1,
        "response": response_payload(status, reason=reason),
    }
