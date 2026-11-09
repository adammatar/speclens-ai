"""Hybrid vector + lexical search with RRF."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import Chunk, ChunkEmbedding, DocumentVersion, Workspace
from app.embeddings.factory import get_embedder
from app.retrieval.rrf import reciprocal_rank_fusion


class SearchError(ValueError):
    """Raised for invalid search requests (fail closed)."""


@dataclass(slots=True)
class SearchHit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    workspace_id: uuid.UUID
    heading_path: str
    page_number: int | None
    excerpt: str
    start_offset: int
    end_offset: int
    rrf_score: float
    vector_rank: int | None = None
    lexical_rank: int | None = None
    vector_distance: float | None = None
    lexical_rank_score: float | None = None


def _excerpt(text: str, limit: int = 320) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def search_chunks(
    session: Session,
    *,
    query: str,
    workspace_id: uuid.UUID,
    document_ids: list[uuid.UUID] | None = None,
    document_version_ids: list[uuid.UUID] | None = None,
    limit: int | None = None,
    debug: bool = False,
    settings: Settings | None = None,
) -> list[SearchHit]:
    """Run hybrid search constrained to a workspace (fail closed if missing)."""
    cfg = settings or get_settings()
    q = query.strip()
    if not q:
        raise SearchError("query must not be empty")

    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise SearchError(f"Workspace not found: {workspace_id}")

    result_limit = limit or cfg.search_result_limit
    vector_limit = cfg.search_vector_limit
    lexical_limit = cfg.search_lexical_limit

    version_filter = select(DocumentVersion.id).where(DocumentVersion.workspace_id == workspace_id)
    if document_ids:
        version_filter = version_filter.where(DocumentVersion.document_id.in_(document_ids))
    if document_version_ids:
        version_filter = version_filter.where(DocumentVersion.id.in_(document_version_ids))

    allowed_version_ids = set(session.scalars(version_filter).all())
    if document_version_ids:
        # Fail closed: reject unknown/out-of-workspace version filters.
        missing = [str(v) for v in document_version_ids if v not in allowed_version_ids]
        if missing:
            raise SearchError(f"document_version_ids not in workspace: {', '.join(missing)}")
    if not allowed_version_ids:
        return []

    embedder = get_embedder(cfg)
    query_vector = embedder.embed_texts([q])[0]

    # Vector channel (cosine distance via pgvector <=> ).
    # Select only chunk_id here: selecting the distance expression can confuse
    # pgvector's result processors when mixed into ORM row mapping.
    distance_expr = ChunkEmbedding.embedding.op("<=>")(query_vector)
    vector_stmt = (
        select(ChunkEmbedding.chunk_id)
        .where(
            ChunkEmbedding.workspace_id == workspace_id,
            ChunkEmbedding.model_name == embedder.model_name,
            ChunkEmbedding.document_version_id.in_(allowed_version_ids),
        )
        .order_by(distance_expr.asc())
        .limit(vector_limit)
    )
    vector_ids = list(session.scalars(vector_stmt).all())
    vector_rank_map = {chunk_id: idx for idx, chunk_id in enumerate(vector_ids, start=1)}
    vector_distance_map: dict[uuid.UUID, float] = {}

    # Lexical channel (Postgres FTS).
    tsq = func.plainto_tsquery("english", q)
    rank_expr = func.ts_rank_cd(Chunk.search_tsv, tsq)
    lexical_stmt = (
        select(
            Chunk.id,
            rank_expr.label("rank_score"),
        )
        .where(
            Chunk.document_version_id.in_(allowed_version_ids),
            Chunk.search_tsv.op("@@")(tsq),
        )
        .order_by(rank_expr.desc())
        .limit(lexical_limit)
    )
    lexical_rows = session.execute(lexical_stmt).all()
    lexical_ids = [row.id for row in lexical_rows]
    lexical_rank_map = {chunk_id: idx for idx, chunk_id in enumerate(lexical_ids, start=1)}
    lexical_score_map = {row.id: float(row.rank_score) for row in lexical_rows}

    fused = reciprocal_rank_fusion(
        [vector_ids, lexical_ids],
        k=cfg.search_rrf_k,
    )[:result_limit]
    if not fused:
        return []

    fused_ids = [chunk_id for chunk_id, _ in fused]

    chunk_rows = session.execute(
        select(
            Chunk,
            DocumentVersion.document_id,
            DocumentVersion.workspace_id,
        )
        .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
        .where(
            Chunk.id.in_(fused_ids),
            DocumentVersion.workspace_id == workspace_id,
        )
    ).all()
    by_id = {chunk.id: (chunk, document_id, ws_id) for chunk, document_id, ws_id in chunk_rows}

    hits: list[SearchHit] = []
    for chunk_id, rrf_score in fused:
        packed = by_id.get(chunk_id)
        if packed is None:
            continue
        chunk, document_id, ws_id = packed
        hit = SearchHit(
            chunk_id=chunk.id,
            document_id=document_id,
            document_version_id=chunk.document_version_id,
            workspace_id=ws_id,
            heading_path=chunk.heading_path,
            page_number=chunk.page_number,
            excerpt=_excerpt(chunk.text),
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            rrf_score=rrf_score,
        )
        if debug:
            hit.vector_rank = vector_rank_map.get(chunk_id)
            hit.lexical_rank = lexical_rank_map.get(chunk_id)
            hit.vector_distance = vector_distance_map.get(chunk_id)
            hit.lexical_rank_score = lexical_score_map.get(chunk_id)
        hits.append(hit)
    return hits
