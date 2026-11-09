"""Pydantic settings for SpecLens API."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    speclens_env: Literal["local", "test", "staging", "production"] = "local"
    speclens_log_level: str = "INFO"
    speclens_api_host: str = "0.0.0.0"
    speclens_api_port: int = 8000
    speclens_deployment_mode: Literal["local", "hosted"] = "local"

    database_url: str = Field(
        default="postgresql+psycopg://speclens:speclens_dev_password@localhost:5432/speclens",
        description="SQLAlchemy database URL",
    )

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    storage_backend: Literal["filesystem"] = "filesystem"
    storage_local_root: str = "./data/storage"

    openai_api_key: str | None = None
    openai_base_url: str | None = None

    @property
    def is_local_mode(self) -> bool:
        return self.speclens_deployment_mode == "local"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
