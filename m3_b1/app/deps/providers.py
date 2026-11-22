import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openai import AsyncOpenAI
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.services.llm import LLMService

SettingsDep = Annotated[Settings, Depends(get_settings)]
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))]


def get_demo_user(credentials: Credentials, settings: SettingsDep) -> str:
    if credentials:
        token = credentials.credentials.encode()
        for owner, secret in (
            ("support-a", settings.demo_token_a),
            ("support-b", settings.demo_token_b),
        ):
            expected = secret.get_secret_value().encode()
            if expected and secrets.compare_digest(token, expected):
                return owner
    raise HTTPException(401, "Требуется учебный токен", headers={"WWW-Authenticate": "Bearer"})


def get_llm(request: Request) -> AsyncOpenAI:
    return request.app.state.llm


def get_cache(request: Request) -> Redis | None:
    return request.app.state.redis


DemoUserDep = Annotated[str, Depends(get_demo_user)]
LLMDep = Annotated[AsyncOpenAI, Depends(get_llm)]
CacheDep = Annotated[Redis | None, Depends(get_cache)]


def get_llm_service(llm: LLMDep, cache: CacheDep, settings: SettingsDep) -> LLMService:
    return LLMService(llm, cache, settings)


LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]
