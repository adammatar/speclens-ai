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
    max_upload_bytes: int = 50 * 1024 * 1024

    openai_api_key: str | None = None
    openai_base_url: str | None = None

    embedding_backend: Literal["stub", "openai"] = "stub"
    embedding_model: str = "speclens-stub-v1"
    embedding_dims: int = 256
    embedding_batch_size: int = 64
    search_vector_limit: int = 30
    search_lexical_limit: int = 30
    search_rrf_k: int = 60
    search_result_limit: int = 12
    search_rerank_enabled: bool = False

    generation_backend: Literal["stub", "openai"] = "stub"
    generation_model: str = "speclens-stub-qa-v1"
    answering_prompt_version: str = "answering-v1"
    qa_context_token_budget: int = 1800
    qa_min_rrf_score: float = 0.01
    qa_max_context_chunks: int = 8

    extraction_backend: Literal["stub", "openai"] = "stub"
    extraction_model: str = "speclens-stub-extract-v1"
    extraction_prompt_version: str = "extraction-v1"

    auth_required: bool = True
    rate_limit_per_minute: int = 120
    retention_days: int = 365

    @property
    def is_local_mode(self) -> bool:
        return self.speclens_deployment_mode == "local"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
