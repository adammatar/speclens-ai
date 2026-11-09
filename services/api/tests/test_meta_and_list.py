"""Meta endpoint and document/conversation list smoke tests."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.ingestion.service import DEFAULT_WORKSPACE_ID, ensure_default_workspace, upload_document
from app.main import create_app
from app.qa.service import create_conversation
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


pytestmark = pytest.mark.skipif(
    not _db_available(DATABASE_URL),
    reason="Postgres not available",
)


def test_meta_is_public(client: TestClient) -> None:
    response = client.get("/api/v1/meta")
    assert response.status_code == 200
    body = response.json()
    assert "retention_days" in body
    assert "version" in body
    assert "openai" not in str(body).lower()


def test_list_documents_and_conversations(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path / "storage"))
    get_settings.cache_clear()
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session: Session = SessionLocal()
    ensure_default_workspace(session)
    session.commit()
    storage = FilesystemStorage(str(tmp_path / "storage"))
    unique = uuid.uuid4().hex
    upload_document(
        session,
        filename=f"list-{unique}.md",
        content_type="text/markdown",
        data=f"# list {unique}\n".encode(),
        title=f"List {unique}",
        workspace_id=DEFAULT_WORKSPACE_ID,
        storage=storage,
    )
    create_conversation(session, workspace_id=DEFAULT_WORKSPACE_ID, title=f"Chat {unique}")
    session.commit()

    with TestClient(create_app()) as client:
        docs = client.get(f"/api/v1/documents?workspace_id={DEFAULT_WORKSPACE_ID}")
        assert docs.status_code == 200
        assert any(row["title"] == f"List {unique}" for row in docs.json())
        convs = client.get(f"/api/v1/conversations?workspace_id={DEFAULT_WORKSPACE_ID}")
        assert convs.status_code == 200
        assert any(row["title"] == f"Chat {unique}" for row in convs.json())

    session.close()
    engine.dispose()
    get_settings.cache_clear()
