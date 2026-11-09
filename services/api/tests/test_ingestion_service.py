"""Ingestion service tests against live Postgres when available."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.models import Chunk, Document, DocumentVersion, IngestionJob, Workspace
from app.ingestion.errors import DuplicateDocumentError
from app.ingestion.hashing import sha256_hex
from app.ingestion.pipeline import run_ingestion_job
from app.ingestion.service import (
    DEFAULT_WORKSPACE_ID,
    delete_document,
    ensure_default_workspace,
    reprocess_document_version,
    upload_document,
)
from app.storage.filesystem import FilesystemStorage

FIXTURES = Path(__file__).parent / "fixtures"


def _db_available(url: str) -> bool:
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:  # noqa: BLE001
        return False


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://speclens:speclens_dev_password@127.0.0.1:5432/speclens",
)

pytestmark = pytest.mark.skipif(
    not _db_available(DATABASE_URL),
    reason="Postgres not available for ingestion service tests",
)


@pytest.fixture
def db_session(tmp_path: Path) -> Session:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    # Ensure default workspace exists (migration may already have seeded it).
    ensure_default_workspace(session)
    session.commit()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=DATABASE_URL,
        storage_local_root=str(tmp_path / "storage"),
        speclens_env="test",
    )


def test_upload_ingest_dedupe_delete_reprocess(
    db_session: Session,
    settings: Settings,
    tmp_path: Path,
) -> None:
    storage = FilesystemStorage(settings.storage_local_root)
    data = (FIXTURES / "sample.md").read_bytes()

    result = upload_document(
        db_session,
        filename="sample.md",
        content_type="text/markdown",
        data=data,
        title="Sample",
        settings=settings,
        storage=storage,
    )
    assert result.sha256 == sha256_hex(data)

    # Run ingest synchronously (no Celery in unit/integration test).
    outcome = run_ingestion_job(db_session, result.job_id, storage=storage)
    assert outcome["status"] == "succeeded"
    chunks = db_session.scalars(
        select(Chunk).where(Chunk.document_version_id == result.document_version_id)
    ).all()
    assert chunks
    assert all(chunk.end_offset >= chunk.start_offset for chunk in chunks)

    with pytest.raises(DuplicateDocumentError):
        upload_document(
            db_session,
            filename="sample-copy.md",
            content_type="text/markdown",
            data=data,
            settings=settings,
            storage=storage,
        )

    reprocess = reprocess_document_version(db_session, result.document_version_id)
    assert reprocess.job_id != result.job_id
    run_ingestion_job(db_session, reprocess.job_id, storage=storage)
    chunks_after = db_session.scalars(
        select(Chunk).where(Chunk.document_version_id == result.document_version_id)
    ).all()
    assert chunks_after

    version = db_session.get(DocumentVersion, result.document_version_id)
    assert version is not None
    storage_key = version.storage_key
    assert storage.exists(storage_key)

    delete_document(db_session, result.document_id, settings=settings, storage=storage)
    assert db_session.get(Document, result.document_id) is None
    assert (
        db_session.scalar(
            select(Chunk).where(Chunk.document_version_id == result.document_version_id)
        )
        is None
    )
    assert not storage.exists(storage_key)

    # Cleanup any leftover jobs referencing deleted rows should already cascade.
    assert db_session.get(Workspace, DEFAULT_WORKSPACE_ID) is not None
    # Avoid unique collisions across test reruns by ensuring no leftover same sha.
    leftover = db_session.scalar(
        select(DocumentVersion).where(DocumentVersion.sha256 == sha256_hex(data))
    )
    assert leftover is None
    _ = uuid.uuid4()  # keep uuid import used for clarity in future extensions
    _ = IngestionJob
