"""Batch embedding pipeline for a document version."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import Chunk, ChunkEmbedding, DocumentVersion
from app.embeddings.base import Embedder
from app.embeddings.factory import get_embedder

logger = logging.getLogger(__name__)


def run_embed_document_version(
    session: Session,
    document_version_id: uuid.UUID,
    *,
    settings: Settings | None = None,
    embedder: Embedder | None = None,
) -> dict[str, object]:
    """Embed all chunks for a document version (idempotent replace per model)."""
    cfg = settings or get_settings()
    engine = embedder or get_embedder(cfg)
    if engine.dims != 256:
        # Model column is Vector(256) in Phase 3 schema.
        raise ValueError(f"Phase 3 schema expects 256-d vectors; got dims={engine.dims}")

    version = session.get(DocumentVersion, document_version_id)
    if version is None:
        raise LookupError(f"Document version not found: {document_version_id}")

    chunks = session.scalars(
        select(Chunk)
        .where(Chunk.document_version_id == document_version_id)
        .order_by(Chunk.chunk_index.asc())
    ).all()
    if not chunks:
        return {
            "status": "succeeded",
            "document_version_id": str(document_version_id),
            "embedded": 0,
        }

    # Replace existing embeddings for this version + model.
    session.execute(
        delete(ChunkEmbedding).where(
            ChunkEmbedding.document_version_id == document_version_id,
            ChunkEmbedding.model_name == engine.model_name,
        )
    )

    batch_size = max(1, cfg.embedding_batch_size)
    embedded = 0
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        texts = [f"{chunk.heading_path}\n{chunk.text}".strip() for chunk in batch]
        vectors = engine.embed_texts(texts)
        for chunk, vector in zip(batch, vectors, strict=True):
            session.add(
                ChunkEmbedding(
                    chunk_id=chunk.id,
                    document_version_id=version.id,
                    workspace_id=version.workspace_id,
                    model_name=engine.model_name,
                    dims=engine.dims,
                    embedding=vector,
                )
            )
            embedded += 1
        session.commit()

    logger.info(
        "embed_succeeded",
        extra={
            "document_version_id": str(document_version_id),
            "embedded": embedded,
            "model_name": engine.model_name,
        },
    )
    return {
        "status": "succeeded",
        "document_version_id": str(document_version_id),
        "embedded": embedded,
        "model_name": engine.model_name,
    }
