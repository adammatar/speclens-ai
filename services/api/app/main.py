"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.routes import documents, health, search
from app.core.config import get_settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.speclens_log_level)
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
    application.include_router(health.router, prefix="/api/v1")
    application.include_router(documents.router, prefix="/api/v1")
    application.include_router(search.router, prefix="/api/v1")
    return application


app = create_app()
