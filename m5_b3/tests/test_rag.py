"""Тесты RAG-endpoint и логики fallback — без сети (ASGITransport + fake-сервис)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.deps.providers import get_rag_service
from app.main import app
from app.services.rag import format_result

_HAPPY = {
    "answer": "Возврат оформляется в течение 14 дней.",
    "top_score": 0.57,
    "sources": [
        {"text": "Возврат денег...", "source": "billing_refunds.md", "score": 0.57},
        {"text": "Способы оплаты...", "source": "billing_payment_methods.md", "score": 0.35},
        {"text": "Сброс пароля...", "source": "support_password_reset.md", "score": 0.28},
    ],
}


class _FakeRAG:
    def __init__(self, result: dict) -> None:
        self._result = result

    async def answer(self, question: str) -> dict:
        return self._result


@pytest.fixture
async def rag_client(request):
    rag = request.param
    app.state.rag_service = rag
    app.dependency_overrides[get_rag_service] = lambda: rag
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.parametrize("rag_client", [_FakeRAG(_HAPPY)], indirect=True)
async def test_rag_query_returns_answer_and_sources(rag_client: AsyncClient) -> None:
    resp = await rag_client.post("/rag/query", json={"question": "за сколько вернут деньги?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert body["top_score"] == 0.57
    assert len(body["sources"]) == 3
    assert body["sources"][0]["source"] == "billing_refunds.md"


@pytest.mark.parametrize("rag_client", [None], indirect=True)
async def test_rag_query_503_when_index_unavailable(rag_client: AsyncClient) -> None:
    resp = await rag_client.post("/rag/query", json={"question": "вопрос"})
    assert resp.status_code == 503


@pytest.mark.parametrize("rag_client", [_FakeRAG(_HAPPY)], indirect=True)
async def test_rag_query_rejects_empty_question(rag_client: AsyncClient) -> None:
    resp = await rag_client.post("/rag/query", json={"question": ""})
    assert resp.status_code == 422


class _Node:
    def __init__(self, text: str, score: float, file_name: str) -> None:
        self.text = text
        self.score = score
        self.metadata = {"file_name": file_name}


class _Response:
    def __init__(self, text: str, nodes: list[_Node]) -> None:
        self._text = text
        self.source_nodes = nodes

    def __str__(self) -> str:
        return self._text


def test_format_result_keeps_answer_above_threshold() -> None:
    response = _Response("ответ строго по контексту", [_Node("чанк", 0.7, "a.md")])
    out = format_result(response, threshold=0.3)
    assert out["answer"] == "ответ строго по контексту"
    assert out["top_score"] == 0.7
    assert out["sources"][0] == {"text": "чанк", "source": "a.md", "score": 0.7}


def test_format_result_falls_back_below_threshold() -> None:
    response = _Response("выдуманный ответ", [_Node("нерелевантный чанк", 0.1, "b.md")])
    out = format_result(response, threshold=0.3)
    assert out["answer"] == "В базе знаний нет ответа на этот вопрос."
    assert out["top_score"] == 0.1


def test_format_result_empty_nodes() -> None:
    out = format_result(_Response("", []), threshold=0.3)
    assert out["top_score"] == 0.0
    assert out["sources"] == []
