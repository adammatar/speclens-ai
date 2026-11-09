"""Cited QA conversation orchestration."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.db.models import (
    Conversation,
    Message,
    MessageCitation,
    MessageRole,
    MessageStatus,
    Workspace,
)
from app.generation.citations import filter_citations
from app.generation.factory import get_generator
from app.qa.context import assemble_context, evidence_is_sufficient
from app.retrieval.search import SearchError

logger = logging.getLogger(__name__)

DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


class QAError(ValueError):
    """Raised for invalid QA requests."""


@dataclass(slots=True)
class AnswerTurn:
    conversation_id: uuid.UUID
    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID
    status: str
    content: str
    retrieval_status: str
    generation_status: str
    retrieved_chunk_ids: list[str]
    citation_chunk_ids: list[str]


def create_conversation(
    session: Session,
    *,
    workspace_id: uuid.UUID | None = None,
    title: str = "New conversation",
) -> Conversation:
    ws_id = workspace_id or DEFAULT_WORKSPACE_ID
    workspace = session.get(Workspace, ws_id)
    if workspace is None:
        raise QAError(f"Workspace not found: {ws_id}")
    conversation = Conversation(workspace_id=ws_id, title=title[:512])
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def get_conversation(session: Session, conversation_id: uuid.UUID) -> Conversation:
    conversation = session.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            selectinload(Conversation.messages).selectinload(Message.citations),
        )
    )
    if conversation is None:
        raise QAError(f"Conversation not found: {conversation_id}")
    return conversation


def post_user_message(
    session: Session,
    conversation_id: uuid.UUID,
    *,
    question: str,
    document_ids: list[uuid.UUID] | None = None,
    document_version_ids: list[uuid.UUID] | None = None,
    settings: Settings | None = None,
) -> AnswerTurn:
    """Persist user+assistant messages for one QA turn (non-stream JSON path)."""
    cfg = settings or get_settings()
    question = question.strip()
    if not question:
        raise QAError("question must not be empty")

    conversation = get_conversation(session, conversation_id)
    started = time.perf_counter()
    prior = [
        (message.role.value, message.content)
        for message in conversation.messages
        if message.role in {MessageRole.USER, MessageRole.ASSISTANT}
    ]

    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=question,
        status=MessageStatus.COMPLETED,
        retrieval_status="not_applicable",
        generation_status="not_applicable",
    )
    session.add(user_msg)
    session.flush()

    assistant = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content="",
        status=MessageStatus.PENDING,
        prompt_version=cfg.answering_prompt_version,
        retrieval_status="running",
        generation_status="pending",
    )
    session.add(assistant)
    session.flush()

    try:
        hits = assemble_context(
            session,
            question=question,
            workspace_id=conversation.workspace_id,
            document_ids=document_ids,
            document_version_ids=document_version_ids,
            settings=cfg,
        )
    except SearchError as exc:
        assistant.status = MessageStatus.FAILED
        assistant.retrieval_status = "failed"
        assistant.generation_status = "skipped"
        assistant.content = str(exc)
        session.commit()
        raise QAError(str(exc)) from exc

    allowlisted = {hit.chunk_id for hit in hits}
    assistant.retrieved_chunk_ids = [str(cid) for cid in allowlisted]
    assistant.retrieval_status = "succeeded" if hits else "empty"

    if not evidence_is_sufficient(hits, cfg):
        assistant.status = MessageStatus.INSUFFICIENT_EVIDENCE
        assistant.generation_status = "skipped"
        assistant.content = (
            "Insufficient evidence: retrieval did not return enough supporting "
            "excerpts to answer this question."
        )
        assistant.model = cfg.generation_model
        assistant.latency_ms = int((time.perf_counter() - started) * 1000)
        session.commit()
        logger.info(
            "qa_insufficient_evidence",
            extra={
                "conversation_id": str(conversation.id),
                "message_id": str(assistant.id),
                "retrieved_count": len(hits),
            },
        )
        return AnswerTurn(
            conversation_id=conversation.id,
            user_message_id=user_msg.id,
            assistant_message_id=assistant.id,
            status=assistant.status.value,
            content=assistant.content,
            retrieval_status=assistant.retrieval_status or "",
            generation_status=assistant.generation_status or "",
            retrieved_chunk_ids=assistant.retrieved_chunk_ids or [],
            citation_chunk_ids=[],
        )

    generator = get_generator(cfg)
    assistant.generation_status = "running"
    session.commit()

    result = generator.generate(
        question=question,
        hits=hits,
        allowlisted_chunk_ids=allowlisted,
        prompt_version=cfg.answering_prompt_version,
        prior_messages=prior,
    )
    safe_citations = filter_citations(result.citations, allowlisted)

    assistant.model = result.model
    assistant.prompt_version = result.prompt_version
    assistant.prompt_tokens = result.prompt_tokens
    assistant.completion_tokens = result.completion_tokens
    assistant.latency_ms = int((time.perf_counter() - started) * 1000)
    assistant.content = result.content
    if result.insufficient_evidence or not safe_citations:
        # If model abstains or all citations were stripped and answer isn't grounded, mark IE.
        if result.insufficient_evidence or not allowlisted:
            assistant.status = MessageStatus.INSUFFICIENT_EVIDENCE
            assistant.generation_status = "insufficient_evidence"
        else:
            assistant.status = MessageStatus.COMPLETED
            assistant.generation_status = "succeeded"
    else:
        assistant.status = MessageStatus.COMPLETED
        assistant.generation_status = "succeeded"

    for draft in safe_citations:
        session.add(
            MessageCitation(
                message_id=assistant.id,
                chunk_id=draft.chunk_id,
                claim_index=draft.claim_index,
                source_quote=draft.source_quote,
            )
        )

    conversation.title = (
        conversation.title if conversation.title != "New conversation" else question[:80]
    )
    session.commit()

    logger.info(
        "qa_turn_completed",
        extra={
            "conversation_id": str(conversation.id),
            "message_id": str(assistant.id),
            "status": assistant.status.value,
            "citation_count": len(safe_citations),
            "latency_ms": assistant.latency_ms,
            "model": assistant.model,
            # Intentionally omit raw document text / full prompts.
        },
    )
    return AnswerTurn(
        conversation_id=conversation.id,
        user_message_id=user_msg.id,
        assistant_message_id=assistant.id,
        status=assistant.status.value,
        content=assistant.content,
        retrieval_status=assistant.retrieval_status or "",
        generation_status=assistant.generation_status or "",
        retrieved_chunk_ids=assistant.retrieved_chunk_ids or [],
        citation_chunk_ids=[str(c.chunk_id) for c in safe_citations],
    )
