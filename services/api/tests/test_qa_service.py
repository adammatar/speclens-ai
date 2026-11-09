"""Cited QA integration tests (requires Postgres)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.embeddings.pipeline import run_embed_document_version
from app.ingestion.pipeline import run_ingestion_job
from app.ingestion.service import ensure_default_workspace, upload_document
from app.qa.service import create_conversation, post_user_message
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
    reason="Postgres not available for QA tests",
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
        embedding_dims=256,
    )


def test_qa_turn_cites_only_retrieved_chunks(
    db_session: Session,
    settings: Settings,
) -> None:
    storage = FilesystemStorage(settings.storage_local_root)
    data = (FIXTURES / "sample.md").read_bytes() + f"\n\nQA marker {uuid.uuid4()}\n".encode()
    uploaded = upload_document(
        db_session,
        filename="sample.md",
        content_type="text/markdown",
        data=data,
        title="QA Doc",
        settings=settings,
        storage=storage,
    )
    run_ingestion_job(db_session, uploaded.job_id, storage=storage)
    run_embed_document_version(db_session, uploaded.document_version_id, settings=settings)

    conversation = create_conversation(db_session, title="QA test")
    turn = post_user_message(
        db_session,
        conversation.id,
        question="What does the system shall accept for Markdown uploads?",
        document_version_ids=[uploaded.document_version_id],
        settings=settings,
    )
    assert turn.status in {"completed", "insufficient_evidence"}
    assert turn.retrieval_status in {"succeeded", "empty"}
    if turn.status == "completed":
        assert turn.citation_chunk_ids
        assert set(turn.citation_chunk_ids).issubset(set(turn.retrieved_chunk_ids))
        assert turn.content


def test_qa_fails_closed_for_foreign_version_filter(
    db_session: Session,
    settings: Settings,
) -> None:
    from app.qa.service import QAError

    conversation = create_conversation(db_session, title="Empty QA")
    with pytest.raises(QAError, match="not in workspace"):
        post_user_message(
            db_session,
            conversation.id,
            question="What is the airspeed velocity of an unladen swallow?",
            document_version_ids=[uuid.uuid4()],
            settings=settings,
        )
