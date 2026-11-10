"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app import __version__
from app.api.routes import (
    comparisons,
    conversations,
    documents,
    evaluation,
    health,
    meta,
    requirements,
    search,
)
from app.core.config import get_settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    import logging
    import os

    from app.core.security_startup import assert_safe_for_hosted
    from app.db.session import SessionLocal

    settings = get_settings()
    configure_logging(settings.speclens_log_level)
    logging.getLogger(__name__).info(
        "speclens_backends embedding=%s generation=%s/%s extraction=%s env_generation=%s",
        settings.embedding_backend,
        settings.generation_backend,
        settings.generation_model,
        settings.extraction_backend,
        os.environ.get("GENERATION_BACKEND"),
    )
    session = SessionLocal()
    try:
        assert_safe_for_hosted(settings, session)
    finally:
        session.close()
    yield


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    application = FastAPI(
        title="SpecLens AI API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.speclens_env != "production" else None,
        redoc_url="/redoc" if settings.speclens_env != "production" else None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router, prefix="/api/v1")
    application.include_router(meta.router, prefix="/api/v1")
    application.include_router(documents.router, prefix="/api/v1")
    application.include_router(search.router, prefix="/api/v1")
    application.include_router(conversations.router, prefix="/api/v1")
    application.include_router(requirements.router, prefix="/api/v1")
    application.include_router(comparisons.router, prefix="/api/v1")
    application.include_router(evaluation.router, prefix="/api/v1")

    def custom_openapi() -> dict[str, Any]:
        if application.openapi_schema:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            routes=application.routes,
        )
        components = schema.setdefault("components", {})
        schemes = components.setdefault("securitySchemes", {})
        schemes["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "description": "API key as Bearer token (local bootstrap: speclens-local-dev-key)",
        }
        schemes["ApiKeyHeader"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Alternate API key header",
        }
        public = {"/api/v1/health", "/api/v1/ready", "/api/v1/meta"}
        for path, methods in schema.get("paths", {}).items():
            if path in public:
                continue
            for operation in methods.values():
                if isinstance(operation, dict):
                    operation["security"] = [{"BearerAuth": []}, {"ApiKeyHeader": []}]
        application.openapi_schema = schema
        return application.openapi_schema

    application.openapi = custom_openapi  # type: ignore[method-assign]
    return application


app = create_app()
