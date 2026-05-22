from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_")

    openai_api_key: SecretStr = SecretStr("sk-test-placeholder")
    default_model: str = "gpt-4o-mini"
    request_timeout: float = 30.0
    max_retries: int = 3


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "llm-service"
    debug: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600
    llm: LLMSettings = Field(default_factory=LLMSettings)

    # Chat ---------------------------------------------------------------
    database_url: str = "postgresql+asyncpg://chat:chat@localhost:5432/chat"
    chat_repository: Literal["json", "postgres"] = "json"
    chat_storage_dir: Path = Path("./var/chats")
    chat_context_window: int = 10

    # Production ---------------------------------------------------------
    # X-Admin-Token для /chats/admin/*. Сменить на 32+ hex-байт через
    # `openssl rand -hex 32` в проде.
    admin_token: SecretStr = SecretStr("change-me-admin")
    # Service-to-service: backend ↔ bot (общий с bot /notify).
    internal_token: SecretStr = SecretStr("change-me-internal")
    # Базовый URL bot-сервиса (для broadcast и notify-вызовов из backend).
    bot_url: str = "http://bot:9000"
    # Telegram chat_id админ-группы для alert drain и handoff-уведомлений.
    admin_chat_id: int | None = None
    # Включить OpenAI Moderation API (layer 2 каскада). Если False —
    # только regex-блоклист.
    moderation_use_openai: bool = True
    # Rate limit: сколько сообщений на одного owner_external_id в минуту.
    rate_limit_messages_per_min: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
