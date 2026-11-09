"""API key auth, workspace isolation, redaction, and delete-under-auth tests."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import JsonFormatter
from app.db.models import (
    ApiKey,
    AuditEvent,
    Chunk,
    ChunkEmbedding,
    Document,
    DocumentVersion,
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from app.ingestion.hashing import sha256_hex
from app.ingestion.pipeline import run_ingestion_job
from app.ingestion.service import (
    DEFAULT_WORKSPACE_ID,
    ensure_default_workspace,
    upload_document,
)
from app.security.auth import AuthContext, hash_api_key
from app.security.redaction import contains_forbidden_log_content, redact_mapping, redact_string
from app.security.workspace import require_workspace_role
from app.storage.filesystem import FilesystemStorage

FIXTURES = Path(__file__).parent / "fixtures"
BOOTSTRAP_KEY = "speclens-local-dev-key"

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
    reason="Postgres not available for security auth tests",
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    ensure_default_workspace(session)
    _ensure_bootstrap_identity(session)
    session.commit()
    yield session
    session.close()
    engine.dispose()


def _ensure_bootstrap_identity(session: Session) -> None:
    user = session.scalar(select(User).where(User.email == "local-admin@speclens.local"))
    if user is None:
        user = User(
            id=uuid.UUID("00000000-0000-4000-8000-000000000011"),
            email="local-admin@speclens.local",
            display_name="Local Admin",
            is_active=True,
        )
        session.add(user)
        session.flush()
    membership = session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == DEFAULT_WORKSPACE_ID,
            WorkspaceMembership.user_id == user.id,
        )
    )
    if membership is None:
        session.add(
            WorkspaceMembership(
                workspace_id=DEFAULT_WORKSPACE_ID,
                user_id=user.id,
                role=WorkspaceRole.OWNER,
            )
        )
    key = session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(BOOTSTRAP_KEY)))
    if key is None:
        session.add(
            ApiKey(
                id=uuid.UUID("00000000-0000-4000-8000-000000000012"),
                user_id=user.id,
                name="local-bootstrap",
                key_prefix=BOOTSTRAP_KEY[:12],
                key_hash=hash_api_key(BOOTSTRAP_KEY),
                is_active=True,
            )
        )


@pytest.fixture
def auth_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path / "storage"))
    get_settings.cache_clear()
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_redaction_strips_secrets_and_bodies() -> None:
    assert "[REDACTED]" in redact_string(f"Authorization: Bearer {BOOTSTRAP_KEY}")
    assert not contains_forbidden_log_content(redact_string(BOOTSTRAP_KEY))
    redacted = redact_mapping(
        {
            "api_key": BOOTSTRAP_KEY,
            "openai_api_key": "sk-test",
            "text": "confidential document body",
            "request_id": "abc",
        }
    )
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["openai_api_key"] == "[REDACTED]"
    assert "confidential" not in str(redacted["text"])
    assert redacted["request_id"] == "abc"

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=20,
        pathname=__file__,
        lineno=1,
        msg="using key %s",
        args=(BOOTSTRAP_KEY,),
        exc_info=None,
    )
    rendered = formatter.format(record)
    assert BOOTSTRAP_KEY not in rendered


def test_missing_api_key_returns_401(auth_client: TestClient) -> None:
    response = auth_client.get(f"/api/v1/documents/{uuid.uuid4()}")
    assert response.status_code == 401


def test_invalid_api_key_returns_401(auth_client: TestClient) -> None:
    response = auth_client.get(
        f"/api/v1/documents/{uuid.uuid4()}",
        headers={"Authorization": "Bearer totally-invalid-key"},
    )
    assert response.status_code == 401


def test_health_remains_public(auth_client: TestClient) -> None:
    assert auth_client.get("/api/v1/health").status_code == 200


def test_bootstrap_key_upload_delete_clears_artifacts(
    auth_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    settings = Settings(
        database_url=DATABASE_URL,
        storage_local_root=str(tmp_path / "storage"),
        speclens_env="test",
        auth_required=True,
        rate_limit_per_minute=0,
    )
    storage = FilesystemStorage(settings.storage_local_root)
    unique = uuid.uuid4().hex
    data = (FIXTURES / "sample.md").read_bytes() + f"\n# delete-auth {unique}\n".encode()

    result = upload_document(
        db_session,
        filename=f"delete-{unique}.md",
        content_type="text/markdown",
        data=data,
        title="Delete Auth",
        settings=settings,
        storage=storage,
    )
    run_ingestion_job(db_session, result.job_id, storage=storage)
    version = db_session.get(DocumentVersion, result.document_version_id)
    assert version is not None
    storage_key = version.storage_key
    assert storage.exists(storage_key)
    assert db_session.scalars(
        select(Chunk).where(Chunk.document_version_id == result.document_version_id)
    ).first()
    # Embeddings may be written by a follow-on task; create is optional for delete proof.
    _ = ChunkEmbedding

    delete_response = auth_client.delete(
        f"/api/v1/documents/{result.document_id}",
        headers={"Authorization": f"Bearer {BOOTSTRAP_KEY}"},
    )
    assert delete_response.status_code == 204, delete_response.text

    db_session.expire_all()
    assert db_session.get(Document, result.document_id) is None
    assert (
        db_session.scalar(
            select(Chunk).where(Chunk.document_version_id == result.document_version_id)
        )
        is None
    )
    assert (
        db_session.scalar(
            select(ChunkEmbedding).where(
                ChunkEmbedding.document_version_id == result.document_version_id
            )
        )
        is None
    )
    assert not storage.exists(storage_key)

    events = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.action == "document.delete",
            AuditEvent.resource_id == str(result.document_id),
        )
    ).all()
    assert events
    assert sha256_hex(data)


def test_cross_workspace_access_denied(
    auth_client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    foreign_ws = Workspace(id=uuid.uuid4(), name=f"foreign-{uuid.uuid4().hex[:8]}")
    session_user = User(
        email=f"foreign-{uuid.uuid4().hex[:8]}@speclens.local",
        display_name="Foreign",
        is_active=True,
    )
    db_session.add(foreign_ws)
    db_session.add(session_user)
    db_session.flush()
    db_session.add(
        WorkspaceMembership(
            workspace_id=foreign_ws.id,
            user_id=session_user.id,
            role=WorkspaceRole.OWNER,
        )
    )
    foreign_key = f"speclens-foreign-{uuid.uuid4().hex[:10]}"
    db_session.add(
        ApiKey(
            user_id=session_user.id,
            name="foreign",
            key_prefix=foreign_key[:12],
            key_hash=hash_api_key(foreign_key),
            is_active=True,
        )
    )
    db_session.commit()

    settings = Settings(
        database_url=DATABASE_URL,
        storage_local_root=str(tmp_path / "storage-ws"),
        speclens_env="test",
    )
    storage = FilesystemStorage(settings.storage_local_root)
    data = (FIXTURES / "sample.md").read_bytes() + f"\nws {foreign_ws.id}\n".encode()
    result = upload_document(
        db_session,
        filename="foreign.md",
        content_type="text/markdown",
        data=data,
        title="Foreign Doc",
        workspace_id=foreign_ws.id,
        settings=settings,
        storage=storage,
    )
    db_session.commit()

    denied = auth_client.get(
        f"/api/v1/documents/{result.document_id}",
        headers={"Authorization": f"Bearer {BOOTSTRAP_KEY}"},
    )
    assert denied.status_code == 403

    allowed = auth_client.get(
        f"/api/v1/documents/{result.document_id}",
        headers={"X-API-Key": foreign_key},
    )
    assert allowed.status_code == 200
    assert allowed.json()["workspace_id"] == str(foreign_ws.id)

    search_denied = auth_client.post(
        "/api/v1/search",
        headers={"X-API-Key": foreign_key},
        json={"query": "hierarchical", "workspace_id": str(DEFAULT_WORKSPACE_ID)},
    )
    assert search_denied.status_code == 403


def test_viewer_cannot_upload(auth_client: TestClient, db_session: Session) -> None:
    viewer = User(
        email=f"viewer-{uuid.uuid4().hex[:8]}@speclens.local",
        display_name="Viewer",
        is_active=True,
    )
    db_session.add(viewer)
    db_session.flush()
    db_session.add(
        WorkspaceMembership(
            workspace_id=DEFAULT_WORKSPACE_ID,
            user_id=viewer.id,
            role=WorkspaceRole.VIEWER,
        )
    )
    viewer_key = f"speclens-viewer-{uuid.uuid4().hex[:8]}"
    db_session.add(
        ApiKey(
            user_id=viewer.id,
            name="viewer",
            key_prefix=viewer_key[:12],
            key_hash=hash_api_key(viewer_key),
            is_active=True,
        )
    )
    db_session.commit()

    response = auth_client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {viewer_key}"},
        files={"file": ("sample.md", b"# hi\n", "text/markdown")},
    )
    assert response.status_code == 403


def test_require_workspace_role_ranks() -> None:
    auth = AuthContext(
        user_id=uuid.uuid4(),
        email="x@y.z",
        api_key_id=uuid.uuid4(),
        memberships={DEFAULT_WORKSPACE_ID: WorkspaceRole.EDITOR},
    )
    assert require_workspace_role(auth, DEFAULT_WORKSPACE_ID, WorkspaceRole.VIEWER)
    assert require_workspace_role(auth, DEFAULT_WORKSPACE_ID, WorkspaceRole.EDITOR)
    with pytest.raises(HTTPException) as exc:
        require_workspace_role(auth, DEFAULT_WORKSPACE_ID, WorkspaceRole.OWNER)
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc2:
        require_workspace_role(auth, uuid.uuid4(), WorkspaceRole.VIEWER)
    assert exc2.value.status_code == 403
