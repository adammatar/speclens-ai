"""Pydantic settings for SpecLens API."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Empty env vars should not override real Docker-injected values with blanks.
        env_ignore_empty=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Process environment (Compose/Docker) must win over any cwd .env file.
        return init_settings, env_settings, dotenv_settings, file_secret_settings

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
    # When true, send dimensions= to /embeddings (OpenAI text-embedding-3*). Gemini usually false.
    embedding_send_dimensions: bool = False
    embedding_batch_size: int = 64
    # Postgres FTS config: simple preserves non-English tokens (Hebrew, etc.).
    search_fts_config: str = "simple"
    search_vector_limit: int = 30
    search_lexical_limit: int = 30
    search_rrf_k: int = 60
    search_result_limit: int = 12
    search_rerank_enabled: bool = False

    # openai = OpenAI Responses API; openai_compat = Chat Completions (Gemini/Ollama/etc.)
    generation_backend: Literal["stub", "openai", "openai_compat"] = "stub"
    generation_model: str = "speclens-stub-qa-v1"
    answering_prompt_version: str = "answering-v1"
    qa_context_token_budget: int = 1800
    qa_min_rrf_score: float = 0.01
    qa_max_context_chunks: int = 8

    extraction_backend: Literal["stub", "openai", "openai_compat"] = "stub"
    extraction_model: str = "speclens-stub-extract-v1"
    extraction_prompt_version: str = "extraction-v1"

    auth_required: bool = True
    rate_limit_per_minute: int = 120
    retention_days: int = 365
    # Destructive retention sweeps are off by default (especially local/dev).
    retention_sweep_enabled: bool = False
    sentry_dsn: str = ""
    # Comma-separated browser origins for the React SPA (local Vite + prod web).
    cors_origins: str = (
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:3000,http://localhost:3000"
    )

    @property
    def is_local_mode(self) -> bool:
        return self.speclens_deployment_mode == "local"

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]

    @model_validator(mode="after")
    def _prefer_process_env_backends(self) -> Settings:
        """Compose injects backends via process env; never let a stray cwd .env win."""
        embed = os.environ.get("EMBEDDING_BACKEND")
        gen = os.environ.get("GENERATION_BACKEND")
        extract = os.environ.get("EXTRACTION_BACKEND")
        model = os.environ.get("GENERATION_MODEL")
        if embed:
            self.embedding_backend = embed  # type: ignore[assignment]
        if gen:
            self.generation_backend = gen  # type: ignore[assignment]
        if extract:
            self.extraction_backend = extract  # type: ignore[assignment]
        if model:
            self.generation_model = model
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
