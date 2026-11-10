"""Retention sweep + Sentry redaction + correlation ID tests."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.models import Document
from app.ingestion.service import ensure_default_workspace
from app.observability.sentry import before_send
from app.retention.service import find_expired_documents, run_retention_sweep
from app.storage.filesystem import FilesystemStorage

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://speclens:speclens_dev_password@127.0.0.1:5432/speclens",
)


def _db_available(url: str) -> bool:
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark_db = pytest.mark.skipif(
    not _db_available(DATABASE_URL),
    reason="Postgres not available",
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    from pgvector.psycopg import register_vector

    @event.listens_for(engine, "connect")
    def _register_vector(dbapi_connection: object, _connection_record: object) -> None:
        register_vector(dbapi_connection)

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    ensure_default_workspace(session)
    session.commit()
    yield session
    session.close()
    engine.dispose()


def test_sentry_before_send_redacts_secrets_and_bodies() -> None:
    event = {
        "request": {
            "headers": {"Authorization": "Bearer secret-token", "X-Request-ID": "abc"},
            "data": {"question": "confidential", "text": "document body"},
        },
        "extra": {"source_quote": "should hide", "request_id": "abc"},
    }
    redacted = before_send(event, None)
    assert redacted is not None
    assert redacted["request"]["headers"]["Authorization"] == "[REDACTED]"
    assert redacted["request"]["headers"]["X-Request-ID"] == "abc"
    assert redacted["request"]["data"] == "[REDACTED]"
    assert redacted["extra"]["source_quote"] == "[REDACTED]"
    assert redacted["extra"]["request_id"] == "abc"


def test_correlation_id_header_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health", headers={"X-Request-ID": "corr-test-1"})
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == "corr-test-1"
    get_settings.cache_clear()


@pytestmark_db
def test_retention_dry_run_and_execute(db_session: Session, tmp_path: Path) -> None:
    workspace = ensure_default_workspace(db_session)
    old = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title=f"old-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(old)
    db_session.flush()
    old.created_at = datetime.now(UTC) - timedelta(days=400)
    db_session.commit()

    settings = Settings(
        database_url=DATABASE_URL,
        storage_local_root=str(tmp_path / "storage"),
        retention_days=30,
        retention_sweep_enabled=True,
        speclens_env="test",
    )
    storage = FilesystemStorage(settings.storage_local_root)

    dry = run_retention_sweep(db_session, dry_run=True, settings=settings, storage=storage)
    assert any(c.document_id == old.id for c in dry.candidates)
    assert dry.deleted_ids == []
    assert db_session.get(Document, old.id) is not None

    executed = run_retention_sweep(db_session, dry_run=False, settings=settings, storage=storage)
    assert old.id in executed.deleted_ids
    assert db_session.get(Document, old.id) is None


@pytestmark_db
def test_find_expired_respects_retention_window(db_session: Session) -> None:
    workspace = ensure_default_workspace(db_session)
    recent = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        title=f"recent-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(recent)
    db_session.flush()
    recent.created_at = datetime.now(UTC) - timedelta(days=2)
    db_session.commit()
    found = find_expired_documents(db_session, retention_days=30)
    assert all(c.document_id != recent.id for c in found)
