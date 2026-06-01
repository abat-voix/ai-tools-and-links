"""Фейковый клиент OpenAI для тестов без сети.

Повторяет ровно тот контракт, которым пользуется `run_agent`:
`client.chat.completions.create(...)` -> объект с `choices[0].message`
(`.content`, `.tool_calls`) и `.usage` (`.prompt_tokens`, `.completion_tokens`),
а каждый tool call — `.id` и `.function` (`.name`, `.arguments` как JSON-строка).
"""

from types import SimpleNamespace


def make_message(content: str | None = None, tool_calls: list | None = None) -> SimpleNamespace:
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def make_tool_call(call_id: str, name: str, arguments: str) -> SimpleNamespace:
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


def make_response(
    message: SimpleNamespace, prompt_tokens: int = 12, completion_tokens: int = 7
) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


class _FakeCompletions:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    """Подменяет OpenAI: отдаёт заранее заданные ответы по очереди."""

    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(responses))
