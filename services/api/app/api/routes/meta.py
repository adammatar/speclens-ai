"""Public deployment metadata for the web UI settings page."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.api.schemas import MetaResponse
from app.core.config import get_settings

router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=MetaResponse)
def get_meta() -> MetaResponse:
    """Non-secret runtime metadata (safe for the browser)."""
    settings = get_settings()
    return MetaResponse(
        version=__version__,
        deployment_mode=settings.speclens_deployment_mode,
        retention_days=settings.retention_days,
        auth_required=settings.auth_required,
        embedding_backend=settings.embedding_backend,
        generation_backend=settings.generation_backend,
        extraction_backend=settings.extraction_backend,
    )
