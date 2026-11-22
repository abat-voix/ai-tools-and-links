from unittest.mock import AsyncMock

import httpx
from fastapi import FastAPI

from app.routers.agent import router


async def test_agent_resume_requires_explicit_decision() -> None:
    app = FastAPI()
    app.include_router(router)
    graph = AsyncMock()
    app.state.agent_graph = graph

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        response = await client.post("/agent/resume", json={"thread_id": "pending-email"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "decision"]
    graph.ainvoke.assert_not_awaited()
