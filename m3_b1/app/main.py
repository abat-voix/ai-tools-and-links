import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import RequestResponseEndpoint

from app.core.config import get_settings
from app.core.exceptions import IncompleteResponseError
from app.routers import chat, health

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    secrets = (
        settings.openai_api_key.get_secret_value(),
        settings.demo_token_a.get_secret_value(),
        settings.demo_token_b.get_secret_value(),
    )
    if not all(secrets) or secrets[1] == secrets[2]:
        raise RuntimeError("Настройте ключ API и два разных токена учебных профилей")
    async with AsyncExitStack() as resources:
        app.state.llm = await resources.enter_async_context(
            AsyncOpenAI(api_key=secrets[0], timeout=settings.request_timeout, max_retries=1)
        )
        app.state.redis = None
        if settings.redis_url:
            cache = Redis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=1.0, socket_timeout=1.0
            )
            resources.push_async_callback(cache.aclose)
            try:
                await cache.ping()
            except RedisError:
                logger.info("Приложение запущено с недоступным кешем")
            app.state.redis = cache
        yield


app = FastAPI(title="Помощник техподдержки", lifespan=lifespan)


@app.middleware("http")
async def observe(request: Request, call_next: RequestResponseEndpoint) -> Response:
    start = time.perf_counter()
    request_id = uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    route = request.scope.get("route")
    logger.info(
        "http method=%s route=%s status=%d duration_ms=%.1f request_id=%s",
        request.method,
        getattr(route, "path", "unknown"),
        response.status_code,
        (time.perf_counter() - start) * 1000,
        request_id,
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = [list(item["loc"]) for item in exc.errors()]
    return JSONResponse({"detail": "Проверьте поля запроса", "fields": fields}, status_code=422)


@app.exception_handler(TimeoutError)
@app.exception_handler(IncompleteResponseError)
@app.exception_handler(APIError)
async def upstream_error(_: Request, exc: Exception) -> JSONResponse:
    status = 504 if isinstance(exc, (APITimeoutError, TimeoutError)) else 503 if isinstance(exc, RateLimitError) else 502
    return JSONResponse({"detail": "Модель сейчас не ответила"}, status_code=status)


app.include_router(chat.router)
app.include_router(health.router)
