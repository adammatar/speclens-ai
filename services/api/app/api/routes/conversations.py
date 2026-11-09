"""Cited QA conversation endpoints."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.schemas import (
    AnswerTurnResponse,
    CitationResponse,
    ConversationDetailResponse,
    ConversationSummaryResponse,
    CreateConversationRequest,
    MessageResponse,
    PostMessageRequest,
)
from app.db.session import get_session
from app.qa.service import QAError, create_conversation, get_conversation, post_user_message

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_conversation_endpoint(
    body: CreateConversationRequest,
    session: Session = Depends(get_session),
) -> ConversationSummaryResponse:
    try:
        conversation = create_conversation(
            session,
            workspace_id=body.workspace_id,
            title=body.title,
        )
    except QAError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ConversationSummaryResponse(
        id=conversation.id,
        workspace_id=conversation.workspace_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation_endpoint(
    conversation_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> ConversationDetailResponse:
    try:
        conversation = get_conversation(session, conversation_id)
    except QAError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    messages: list[MessageResponse] = []
    for message in conversation.messages:
        messages.append(
            MessageResponse(
                id=message.id,
                role=message.role.value,
                content=message.content,
                status=message.status.value,
                model=message.model,
                prompt_version=message.prompt_version,
                retrieved_chunk_ids=message.retrieved_chunk_ids,
                retrieval_status=message.retrieval_status,
                generation_status=message.generation_status,
                latency_ms=message.latency_ms,
                prompt_tokens=message.prompt_tokens,
                completion_tokens=message.completion_tokens,
                citations=[
                    CitationResponse(
                        chunk_id=citation.chunk_id,
                        claim_index=citation.claim_index,
                        source_quote=citation.source_quote,
                    )
                    for citation in message.citations
                ],
                created_at=message.created_at,
            )
        )
    return ConversationDetailResponse(
        id=conversation.id,
        workspace_id=conversation.workspace_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


@router.post("/{conversation_id}/messages", response_model=AnswerTurnResponse)
def post_message_endpoint(
    conversation_id: uuid.UUID,
    body: PostMessageRequest,
    session: Session = Depends(get_session),
) -> AnswerTurnResponse | StreamingResponse:
    if body.stream:
        return StreamingResponse(
            _stream_answer(session, conversation_id, body),
            media_type="text/event-stream",
        )
    try:
        turn = post_user_message(
            session,
            conversation_id,
            question=body.question,
            document_ids=body.document_ids,
            document_version_ids=body.document_version_ids,
        )
    except QAError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AnswerTurnResponse(
        conversation_id=turn.conversation_id,
        user_message_id=turn.user_message_id,
        assistant_message_id=turn.assistant_message_id,
        status=turn.status,
        content=turn.content,
        retrieval_status=turn.retrieval_status,
        generation_status=turn.generation_status,
        retrieved_chunk_ids=turn.retrieved_chunk_ids,
        citation_chunk_ids=turn.citation_chunk_ids,
    )


def _stream_answer(
    session: Session,
    conversation_id: uuid.UUID,
    body: PostMessageRequest,
) -> Iterator[str]:
    """SSE stream: status events then token chunks, then final JSON."""
    try:
        turn = post_user_message(
            session,
            conversation_id,
            question=body.question,
            document_ids=body.document_ids,
            document_version_ids=body.document_version_ids,
        )
    except QAError as exc:
        payload = {"event": "error", "detail": str(exc)}
        yield f"data: {json.dumps(payload)}\n\n"
        return

    yield f"data: {json.dumps({'event': 'retrieval', 'status': turn.retrieval_status})}\n\n"
    yield f"data: {json.dumps({'event': 'generation', 'status': turn.generation_status})}\n\n"
    # Naive token stream for UI progress (answer already computed in stub/openai path).
    for token in turn.content.split(" "):
        yield f"data: {json.dumps({'event': 'token', 'text': token + ' '})}\n\n"
    final = {
        "event": "final",
        "conversation_id": str(turn.conversation_id),
        "assistant_message_id": str(turn.assistant_message_id),
        "status": turn.status,
        "content": turn.content,
        "retrieved_chunk_ids": turn.retrieved_chunk_ids,
        "citation_chunk_ids": turn.citation_chunk_ids,
        "retrieval_status": turn.retrieval_status,
        "generation_status": turn.generation_status,
    }
    yield f"data: {json.dumps(final)}\n\n"
