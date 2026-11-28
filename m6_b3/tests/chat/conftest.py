"""Фикстуры для chat-тестов."""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.chat.deps import get_chat_service, get_repository
from app.chat.repositories.json_repo import JsonChatRepository
from app.chat.service import ChatService
from app.deps.providers import get_cache, get_llm
from app.main import app
from tests.response_fixtures import MockTextStream


@pytest.fixture
def json_repo(tmp_path):
    return JsonChatRepository(base_dir=tmp_path / "chats")


@pytest.fixture
def mock_llm_stream():
    """Мок AsyncOpenAI с новым стримом на каждый вызов."""
    llm = AsyncMock()
    llm.responses.create = AsyncMock(
        side_effect=lambda **_: MockTextStream("При", "вет", "!")
    )
    return llm


@pytest.fixture
async def chat_client(json_repo, mock_llm_stream):
    """HTTP-клиент с подменёнными зависимостями (json-repo + mock LLM)."""
    chat_service = ChatService(
        repository=json_repo,
        llm_client=mock_llm_stream,
        context_window=10,
        default_model="gpt-6-luna",
    )

    # Заготовка state — на случай если что-то всё ещё дёргает app.state.
    app.state.llm = mock_llm_stream
    app.state.redis = None
    app.state.session_factory = None
    app.state.async_engine = None

    async def _override_repo():
        yield json_repo

    app.dependency_overrides[get_repository] = _override_repo
    app.dependency_overrides[get_chat_service] = lambda: chat_service
    app.dependency_overrides[get_llm] = lambda: mock_llm_stream
    app.dependency_overrides[get_cache] = lambda: None

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac, chat_service

    app.dependency_overrides.clear()
