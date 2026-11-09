"""Hybrid search integration tests (requires Postgres + pgvector)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.models import ChunkEmbedding, Workspace
from app.embeddings.pipeline import run_embed_document_version
from app.ingestion.pipeline import run_ingestion_job
from app.ingestion.service import ensure_default_workspace, upload_document
from app.retrieval.search import SearchError, search_chunks
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
    reason="Postgres not available for search tests",
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    from pgvector.psycopg import register_vector
    from sqlalchemy import event

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
        embedding_model="speclens-stub-v1",
        embedding_dims=256,
    )


def test_hybrid_search_returns_provenance_and_isolates_workspace(
    db_session: Session,
    settings: Settings,
) -> None:
    storage = FilesystemStorage(settings.storage_local_root)
    data = (FIXTURES / "sample.md").read_bytes()
    # Unique content to avoid SHA collisions across runs.
    unique = data + f"\n\nUnique marker {uuid.uuid4()}\n".encode()

    result = upload_document(
        db_session,
        filename="sample.md",
        content_type="text/markdown",
        data=unique,
        title="Search Sample",
        settings=settings,
        storage=storage,
    )
    run_ingestion_job(db_session, result.job_id, storage=storage)
    embed_result = run_embed_document_version(
        db_session,
        result.document_version_id,
        settings=settings,
    )
    assert int(embed_result["embedded"]) > 0
    emb_count = db_session.scalar(
        select(func.count())
        .select_from(ChunkEmbedding)
        .where(ChunkEmbedding.document_version_id == result.document_version_id)
    )
    assert emb_count and emb_count > 0

    hits = search_chunks(
        db_session,
        query="hierarchical chunking heading paths",
        workspace_id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
        document_version_ids=[result.document_version_id],
        settings=settings,
        debug=True,
    )
    assert hits
    hit = hits[0]
    assert hit.document_id == result.document_id
    assert hit.document_version_id == result.document_version_id
    assert hit.excerpt
    assert hit.heading_path is not None
    assert hit.end_offset >= hit.start_offset
    assert hit.rrf_score > 0
    assert all(h.document_version_id == result.document_version_id for h in hits)

    # Workspace isolation: unknown workspace fails closed.
    with pytest.raises(SearchError, match="Workspace not found"):
        search_chunks(
            db_session,
            query="hierarchical chunking",
            workspace_id=uuid.uuid4(),
            settings=settings,
        )

    # Foreign workspace with no docs returns empty, not other workspace hits.
    other = Workspace(id=uuid.uuid4(), name=f"other-{uuid.uuid4().hex[:8]}")
    db_session.add(other)
    db_session.commit()
    empty = search_chunks(
        db_session,
        query="hierarchical chunking heading paths",
        workspace_id=other.id,
        settings=settings,
    )
    assert empty == []
