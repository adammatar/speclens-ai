"""Celery application for SpecLens workers.

Uses Redis as a persistent broker so jobs survive worker restarts.
"""

from __future__ import annotations

import os

from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

app = Celery(
    "speclens",
    broker=broker_url,
    backend=result_backend,
    include=["speclens_worker.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Optional Sentry for workers (no-op when SENTRY_DSN is empty).
try:
    from app.core.config import get_settings
    from app.observability.sentry import init_sentry

    _settings = get_settings()
    init_sentry(
        dsn=_settings.sentry_dsn,
        environment=_settings.speclens_env,
        service="worker",
    )
except Exception:  # noqa: BLE001
    pass
