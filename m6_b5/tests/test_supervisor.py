"""Структурный тест мультиагентного супервизора — без сети.

Полный прогон (супервизор → researcher → writer) требует реальной модели и
проверяется вживую / через scripts/multi_agent_demo.py. Здесь — что граф
собирается и содержит нужные узлы.
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.agents.supervisor import build_supervisor, extract_final_answer


async def _fake_search(query: str) -> dict:
    return {
        "answer": "Срок возврата — 14 дней.",
        "sources": [{"id": 1, "file_name": "refunds.md"}],
        "confident": True,
    }


def test_build_supervisor_compiles_with_expected_nodes():
    model = ChatOpenAI(model="gpt-6-luna", api_key="sk-placeholder")

    app = build_supervisor(model, _fake_search)

    nodes = set(app.get_graph().nodes)
    assert {"supervisor", "researcher", "writer"} <= nodes


def _supervisor_history() -> list:
    """История, которую create_supervisor реально оставляет после прогона.

    Порядок и служебные сообщения записаны с живого графа: воркеры возвращают
    управление через transfer_back_to_supervisor, последним идёт пустой ход
    супервизора.
    """
    return [
        HumanMessage("Каков срок возврата?"),
        AIMessage("", name="supervisor", tool_calls=[
            {"name": "transfer_to_researcher", "args": {}, "id": "c1", "type": "tool_call"}]),
        ToolMessage("Successfully transferred to researcher", tool_call_id="c1"),
        AIMessage("- срок возврата 14 дней [1]", name="researcher"),
        AIMessage("Transferring back to supervisor", name="researcher", tool_calls=[
            {"name": "transfer_back_to_supervisor", "args": {}, "id": "c2", "type": "tool_call"}]),
        ToolMessage("Successfully transferred back to supervisor", tool_call_id="c2"),
        AIMessage("", name="supervisor", tool_calls=[
            {"name": "transfer_to_writer", "args": {}, "id": "c3", "type": "tool_call"}]),
        ToolMessage("Successfully transferred to writer", tool_call_id="c3"),
        AIMessage("Возврат средств возможен в течение 14 дней [1].", name="writer"),
        AIMessage("Transferring back to supervisor", name="writer", tool_calls=[
            {"name": "transfer_back_to_supervisor", "args": {}, "id": "c4", "type": "tool_call"}]),
        ToolMessage("Successfully transferred back to supervisor", tool_call_id="c4"),
        AIMessage("", name="supervisor"),
    ]


def test_extract_final_answer_returns_writer_message_not_last():
    history = _supervisor_history()

    assert history[-1].content == ""  # последнее сообщение — пустой ход супервизора
    assert extract_final_answer(history) == "Возврат средств возможен в течение 14 дней [1]."


def test_extract_final_answer_skips_writer_handoff_back():
    """Служебная реплика writer'а с tool_calls не должна попадать в ответ."""
    history = _supervisor_history()

    assert "Transferring back" not in extract_final_answer(history)


def test_extract_final_answer_empty_when_writer_never_spoke():
    history = [HumanMessage("вопрос"), AIMessage("", name="supervisor")]

    assert extract_final_answer(history) == ""


def test_extract_final_answer_uses_text_blocks_only():
    messages = [AIMessage(name='writer', content=[
        {'type':'reasoning', 'summary':[{'type':'summary_text','text':'Служебное'}]},
        {'type':'text', 'text':'Ответ с источником [1].'},
    ])]
    assert extract_final_answer(messages) == 'Ответ с источником [1].'


async def test_full_supervisor_routes_research_then_writer():
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel

    class ToolModel(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    def call(name, args, cid):
        return AIMessage('', tool_calls=[{'name':name,'args':args,'id':cid,'type':'tool_call'}])

    model = ToolModel(responses=[
        call('transfer_to_researcher', {}, 'r'),
        call('search_knowledge_base', {'query':'срок возврата'}, 'kb'),
        AIMessage('Срок возврата — 14 дней [1].'),
        call('transfer_to_writer', {}, 'w'),
        AIMessage('Возврат возможен 14 дней [1].'),
        AIMessage(''),
    ])
    queries = []
    async def search(query):
        queries.append(query)
        return await _fake_search(query)
    graph = build_supervisor(model, search)
    result = await graph.ainvoke({'messages':[HumanMessage('Срок возврата?')]},
                                {'configurable':{'thread_id':'workflow-test'},
                                 'recursion_limit':40})
    assert extract_final_answer(result['messages']) == 'Возврат возможен 14 дней [1].'
    assert queries == ['срок возврата']
