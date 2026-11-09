"""Version comparison pipeline tests (requires Postgres)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.compare.pipeline import (
    create_comparison_job,
    decide_change,
    get_comparison_job,
    run_comparison_job,
)
from app.core.config import Settings
from app.embeddings.pipeline import run_embed_document_version
from app.extraction.pipeline import create_extraction_job, run_extraction_job
from app.ingestion.pipeline import run_ingestion_job
from app.ingestion.service import ensure_default_workspace, upload_document, upload_document_version
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
    reason="Postgres not available for compare tests",
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


def _ready_version(
    session: Session, settings: Settings, data: bytes, title: str
) -> tuple[uuid.UUID, uuid.UUID]:
    storage = FilesystemStorage(settings.storage_local_root)
    uploaded = upload_document(
        session,
        filename="sample.md",
        content_type="text/markdown",
        data=data,
        title=title,
        settings=settings,
        storage=storage,
    )
    run_ingestion_job(session, uploaded.job_id, storage=storage)
    run_embed_document_version(session, uploaded.document_version_id, settings=settings)
    job = create_extraction_job(session, uploaded.document_version_id, settings=settings)
    result = run_extraction_job(session, job.id, settings=settings)
    assert result["status"] == "succeeded"
    return uploaded.document_version_id, uploaded.document_id


def test_compare_links_sources_and_confirm_marks_eval(
    db_session: Session,
    settings: Settings,
) -> None:
    base_text = (FIXTURES / "sample.md").read_bytes() + f"\n\nBase {uuid.uuid4()}\n".encode()
    base_version_id, document_id = _ready_version(db_session, settings, base_text, "Compare Base")

    # New version with minor wording change + one added requirement sentence.
    v2 = (FIXTURES / "sample.md").read_text(encoding="utf-8")
    v2 = v2.replace(
        "preserve heading paths on every chunk",
        "preserve heading paths on every chunk for navigation",
    )
    v2 += "\nThe system shall emit structured audit events for rejected uploads.\n"
    v2 += f"\nTarget {uuid.uuid4()}\n"
    storage = FilesystemStorage(settings.storage_local_root)
    uploaded = upload_document_version(
        db_session,
        document_id,
        filename="sample-v2.md",
        content_type="text/markdown",
        data=v2.encode(),
        settings=settings,
        storage=storage,
    )
    run_ingestion_job(db_session, uploaded.job_id, storage=storage)
    run_embed_document_version(db_session, uploaded.document_version_id, settings=settings)
    job = create_extraction_job(db_session, uploaded.document_version_id, settings=settings)
    assert run_extraction_job(db_session, job.id, settings=settings)["status"] == "succeeded"

    cmp_job = create_comparison_job(
        db_session,
        base_document_version_id=base_version_id,
        target_document_version_id=uploaded.document_version_id,
    )
    outcome = run_comparison_job(db_session, cmp_job.id)
    assert outcome["status"] == "succeeded"

    detail = get_comparison_job(db_session, cmp_job.id)
    assert detail.change_count >= 1
    assert detail.changes

    # Non add/remove changes must link both source texts.
    for change in detail.changes:
        if change.category.value in {"added", "removed"}:
            assert change.old_source_quote or change.new_source_quote
        else:
            assert change.old_source_quote
            assert change.new_source_quote

    # Minor wording should not produce only unpaired add+remove for that requirement.
    categories = {c.category.value for c in detail.changes}
    assert "clarified" in categories or "behavior_changed" in categories or "added" in categories

    target = detail.changes[0]
    decided = decide_change(db_session, target.id, decision="confirmed")
    assert decided.decision.value == "confirmed"
    assert decided.is_eval_example is True
