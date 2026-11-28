"""Подмена клиента Responses для тестов без сети."""

from types import SimpleNamespace


def make_message(content: str | None = None, tool_calls: list | None = None) -> SimpleNamespace:
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def make_tool_call(call_id: str, name: str, arguments: str) -> SimpleNamespace:
    return SimpleNamespace(type="function_call", call_id=call_id, name=name, arguments=arguments)


def make_response(
    message: SimpleNamespace, input_tokens: int = 12, output_tokens: int = 7
) -> SimpleNamespace:
    return SimpleNamespace(
        status="completed",
        incomplete_details=None,
        output=message.tool_calls or [],
        output_text=message.content or "",
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


class _FakeResponses:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    """Отдаёт заранее заданные ответы по очереди."""

    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.responses = _FakeResponses(responses)
