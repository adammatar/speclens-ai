"""Worker task definitions (Phase 1: no-op scaffold only)."""

from __future__ import annotations

import logging
from typing import Any

from speclens_worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="speclens.noop")  # type: ignore[untyped-decorator]
def noop_job(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """No-op job used to prove the worker can dequeue and acknowledge work."""
    data = payload or {}
    logger.info("noop_job_executed", extra={"payload_keys": sorted(data.keys())})
    return {"status": "ok", "echo": data}
