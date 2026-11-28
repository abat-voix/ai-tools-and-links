from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr
    openai_model: str = "gpt-6.2-sol"
    demo_token_a: SecretStr
    demo_token_b: SecretStr
    redis_url: str = ""
    request_timeout: float = Field(default=20, gt=0)
    cache_ttl_seconds: int = Field(default=300, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
