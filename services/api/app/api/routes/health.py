"""Health and readiness endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe - process is up (does not check dependencies)."""
    return {"status": "ok"}


def _redis_up(redis_url: str) -> bool:
    try:
        import redis

        client = redis.Redis.from_url(redis_url, socket_connect_timeout=1)
        client.ping()
        return True
    except Exception:  # noqa: BLE001
        return False


@router.get("/ready")
def ready(response: Response) -> dict[str, Any]:
    """Readiness probe - fails closed until required dependencies are reachable."""
    settings = get_settings()
    checks: dict[str, str] = {}
    ok = True

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "up"
    except Exception as exc:  # noqa: BLE001
        logger.warning("readiness_database_failed", extra={"error": str(exc)})
        checks["database"] = "down"
        ok = False

    if _redis_up(settings.redis_url):
        checks["redis"] = "up"
    else:
        checks["redis"] = "down"
        # Local/test may run API without Redis; require Redis in hosted/production.
        require_redis = (
            settings.speclens_deployment_mode == "hosted"
            or settings.speclens_env == "production"
        )
        if require_redis:
            ok = False

    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", **checks}
    return {"status": "ok", **checks}
