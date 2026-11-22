from fastapi import APIRouter, HTTPException
from redis.exceptions import RedisError

from app.deps.providers import CacheDep, SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(cache: CacheDep, settings: SettingsDep) -> dict[str, str]:
    if settings.redis_url:
        try:
            if cache is None or not await cache.ping():
                raise HTTPException(503, "Кеш недоступен")
        except RedisError as exc:
            raise HTTPException(503, "Кеш недоступен") from exc
    return {"status": "ready"}
