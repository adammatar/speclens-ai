"""Hybrid search endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import SearchHitResponse, SearchRequest, SearchResponse
from app.db.models import WorkspaceRole
from app.db.session import get_session
from app.retrieval.search import SearchError, search_chunks
from app.security.auth import AuthContext, require_api_key
from app.security.workspace import require_workspace_role

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search_endpoint(
    body: SearchRequest,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> SearchResponse:
    require_workspace_role(auth, body.workspace_id, WorkspaceRole.VIEWER)
    try:
        hits = search_chunks(
            session,
            query=body.query,
            workspace_id=body.workspace_id,
            document_ids=body.document_ids,
            document_version_ids=body.document_version_ids,
            limit=body.limit,
            debug=body.debug,
        )
    except SearchError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return SearchResponse(
        query=body.query,
        workspace_id=body.workspace_id,
        results=[
            SearchHitResponse(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                document_version_id=hit.document_version_id,
                workspace_id=hit.workspace_id,
                heading_path=hit.heading_path,
                page_number=hit.page_number,
                excerpt=hit.excerpt,
                start_offset=hit.start_offset,
                end_offset=hit.end_offset,
                rrf_score=hit.rrf_score,
                vector_rank=hit.vector_rank,
                lexical_rank=hit.lexical_rank,
                vector_distance=hit.vector_distance,
                lexical_rank_score=hit.lexical_rank_score,
            )
            for hit in hits
        ],
    )


@router.post("/debug", response_model=SearchResponse)
def search_debug_endpoint(
    body: SearchRequest,
    session: Session = Depends(get_session),
    auth: AuthContext = Depends(require_api_key),
) -> SearchResponse:
    """Same as search with per-channel ranks/scores forced on."""
    debug_body = body.model_copy(update={"debug": True})
    return search_endpoint(debug_body, session, auth)
