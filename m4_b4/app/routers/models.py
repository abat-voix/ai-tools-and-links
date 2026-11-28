from fastapi import APIRouter

from app.deps.providers import SettingsDep
from app.schemas.models import ModelInfo

router = APIRouter(prefix="/models", tags=["models"])

CATALOG: dict[str, ModelInfo] = {
    "gpt-6-luna": ModelInfo(
        id="gpt-6-luna",
        provider="openai",
        input_per_1m=0.10,
        output_per_1m=0.50,
        context_window=1_050_000,
    ),
    "gpt-6.2-sol": ModelInfo(
        id="gpt-6.2-sol",
        provider="openai",
        input_per_1m=2.00,
        output_per_1m=10.00,
        context_window=1_050_000,
    ),
}


@router.get("", response_model=list[ModelInfo])
async def list_models(settings: SettingsDep) -> list[ModelInfo]:
    return list(CATALOG.values())
