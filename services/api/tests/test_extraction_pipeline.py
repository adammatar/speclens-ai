"""Requirement extraction pipeline tests (requires Postgres)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.embeddings.pipeline import run_embed_document_version
from app.extraction.pipeline import create_extraction_job, run_extraction_job
from app.extraction.service import edit_requirement, export_requirements, list_requirements
from app.ingestion.pipeline import run_ingestion_job
from app.ingestion.service import ensure_default_workspace, upload_document
from app.storage.filesystem import FilesystemStorage

FIXTURES = Path(__file__).parent / "fixtures"
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
    reason="Postgres not available for extraction tests",
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


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=DATABASE_URL,
        storage_local_root=str(tmp_path / "storage"),
        speclens_env="test",
        embedding_backend="stub",
        generation_backend="stub",
        extraction_backend="stub",
        embedding_dims=256,
    )


def _ingest_sample(session: Session, settings: Settings) -> uuid.UUID:
    storage = FilesystemStorage(settings.storage_local_root)
    data = (FIXTURES / "sample.md").read_bytes() + f"\n\nExtract {uuid.uuid4()}\n".encode()
    uploaded = upload_document(
        session,
        filename="sample.md",
        content_type="text/markdown",
        data=data,
        title="Extract Doc",
        settings=settings,
        storage=storage,
    )
    run_ingestion_job(session, uploaded.job_id, storage=storage)
    run_embed_document_version(session, uploaded.document_version_id, settings=settings)
    return uploaded.document_version_id


def test_extraction_produces_quoted_requirements(
    db_session: Session,
    settings: Settings,
) -> None:
    version_id = _ingest_sample(db_session, settings)
    job = create_extraction_job(db_session, version_id, settings=settings)
    result = run_extraction_job(db_session, job.id, settings=settings)
    assert result["status"] == "succeeded"
    rows = list_requirements(db_session, document_version_id=version_id)
    assert rows
    for row in rows:
        assert row.sources
        assert any(
            isinstance(src, dict) and str(src.get("source_quote") or "").strip()
            for src in row.sources
        )
        assert row.original_payload


def test_edit_preserves_original_payload_and_accept_marks_eval(
    db_session: Session,
    settings: Settings,
) -> None:
    version_id = _ingest_sample(db_session, settings)
    job = create_extraction_job(db_session, version_id, settings=settings)
    run_extraction_job(db_session, job.id, settings=settings)
    rows = list_requirements(db_session, document_version_id=version_id)
    assert rows
    target = rows[0]
    original = dict(target.original_payload)
    edited = edit_requirement(
        db_session,
        target.id,
        statement=f"{target.statement} (human edit)",
    )
    assert edited.review_state.value == "edited"
    assert edited.original_payload == original
    accepted = edit_requirement(db_session, target.id, review_state="accepted")
    assert accepted.review_state.value == "accepted"
    assert accepted.is_eval_example is True
    assert accepted.original_payload == original


def test_extraction_resumes_after_failure(
    db_session: Session,
    settings: Settings,
) -> None:
    version_id = _ingest_sample(db_session, settings)
    job = create_extraction_job(db_session, version_id, settings=settings)
    assert job.section_total >= 2
    failed = run_extraction_job(
        db_session,
        job.id,
        settings=settings,
        fail_after_sections=1,
    )
    assert failed["status"] == "failed"
    db_session.refresh(job)
    assert job.section_cursor == 1
    resumed = run_extraction_job(db_session, job.id, settings=settings)
    assert resumed["status"] == "succeeded"
    db_session.refresh(job)
    assert job.section_cursor == job.section_total


def test_export_json_and_csv(db_session: Session, settings: Settings) -> None:
    version_id = _ingest_sample(db_session, settings)
    job = create_extraction_job(db_session, version_id, settings=settings)
    run_extraction_job(db_session, job.id, settings=settings)
    media, body = export_requirements(
        db_session,
        format="json",
        document_version_id=version_id,
    )
    assert media == "application/json"
    assert "source_quote" in body or "sources" in body
    media_csv, csv_body = export_requirements(
        db_session,
        format="csv",
        document_version_id=version_id,
    )
    assert media_csv == "text/csv"
    assert "statement" in csv_body
