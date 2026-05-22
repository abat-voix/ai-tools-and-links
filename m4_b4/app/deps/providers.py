"""Глобальные FastAPI-зависимости.

Всё, что лежит в `app.state` (LLM-клиент, Redis, session_factory), достаём
через `Depends`-провайдеры — это даёт тип-чек и убирает getattr из роутов.
Lifespan гарантирует, что атрибуты на app.state выставлены: для боевых
клиентов — реальный объект, для опциональных (Redis/Postgres) — `None`.
"""

from typing import Annotated, Any

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.services.llm import LLMService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_llm(request: Request) -> Any:
    return request.app.state.llm


def get_cache(request: Request) -> Any:
    return request.app.state.redis


def get_session_factory(request: Request) -> Any:
    """Возвращает async_sessionmaker, выставленный в lifespan, либо None,
    если Postgres недоступен. Роуты, которым PG обязателен, должны явно
    проверять на None и отдавать 503/собственный fallback."""
    return request.app.state.session_factory


LLMDep = Annotated[Any, Depends(get_llm)]
CacheDep = Annotated[Any, Depends(get_cache)]
SessionFactoryDep = Annotated[Any, Depends(get_session_factory)]


def get_llm_service(
    llm: LLMDep,
    cache: CacheDep,
    settings: SettingsDep,
) -> LLMService:
    return LLMService(llm=llm, cache=cache, ttl=settings.cache_ttl_seconds)


LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]
