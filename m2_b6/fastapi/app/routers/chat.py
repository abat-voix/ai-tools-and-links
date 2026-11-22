import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import APIError

from app.core.exceptions import IncompleteResponseError
from app.deps.providers import DemoUserDep, LLMServiceDep
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(request: ChatRequest, service: LLMServiceDep, user_id: DemoUserDep) -> ChatResponse:
    return await service.complete(request, user_id)


@router.post("/stream")
async def chat_stream(
    request: ChatRequest, service: LLMServiceDep, user_id: DemoUserDep
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        try:
            async for kind, value in service.stream(request):
                payload = json.dumps({"content": value}, ensure_ascii=False) if kind == "delta" else value
                yield f"event: {kind}\ndata: {payload}\n\n"
        except (APIError, IncompleteResponseError):
            yield 'event: error\ndata: {"code":"upstream_error"}\n\n'
            return
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
