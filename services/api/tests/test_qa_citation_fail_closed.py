"""Regression: completed QA turns require allow-listed citations (fail closed)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from app.db.models import MessageStatus
from app.generation.base import CitationDraft, GenerationResult
from app.generation.citations import filter_citations
from app.qa.citation_policy import resolve_answer_status
from app.retrieval.search import SearchHit


def test_resolve_answer_status_requires_citations() -> None:
    assert (
        resolve_answer_status(generator_insufficient_evidence=False, safe_citation_count=1)
        is MessageStatus.COMPLETED
    )
    assert (
        resolve_answer_status(generator_insufficient_evidence=False, safe_citation_count=0)
        is MessageStatus.INSUFFICIENT_EVIDENCE
    )
    assert (
        resolve_answer_status(generator_insufficient_evidence=True, safe_citation_count=2)
        is MessageStatus.INSUFFICIENT_EVIDENCE
    )


def test_filter_keeps_only_allowlisted() -> None:
    good = uuid.uuid4()
    forged = uuid.uuid4()
    out = filter_citations(
        [
            CitationDraft(chunk_id=good, claim_index=0),
            CitationDraft(chunk_id=forged, claim_index=1),
        ],
        {good},
    )
    assert [c.chunk_id for c in out] == [good]


def _hit(chunk_id: uuid.UUID) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        document_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        heading_path="Spec",
        page_number=1,
        excerpt="The system shall accept Markdown uploads.",
        start_offset=0,
        end_offset=40,
        rrf_score=0.05,
    )


class _FakeGenerator:
    def __init__(self, result: GenerationResult) -> None:
        self._result = result
        self.model_name = result.model or "fake-model"

    def generate(self, **_kwargs: Any) -> GenerationResult:
        return self._result


def _run_turn(
    *,
    hits: list[SearchHit],
    generation: GenerationResult,
) -> Any:
    """Drive post_user_message with mocked retrieval + generator (no Postgres)."""
    from app.qa import service as qa_service

    conversation_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    assistant_id = uuid.uuid4()

    conversation = SimpleNamespace(
        id=conversation_id,
        workspace_id=workspace_id,
        title="New conversation",
        messages=[],
    )

    stored: dict[str, Any] = {"citations": []}

    class _Session:
        def add(self, obj: Any) -> None:
            if obj.__class__.__name__ == "MessageCitation":
                stored["citations"].append(obj)

        def flush(self) -> None:
            return None

        def commit(self) -> None:
            return None

        def get(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    session = _Session()

    def _fake_get_conversation(_session: Any, _cid: uuid.UUID) -> Any:
        return conversation

    # Assign IDs as ORM would after flush
    def _add_side_effect(obj: Any) -> None:
        name = obj.__class__.__name__
        if name == "Message":
            if getattr(obj, "role", None) and obj.role.value == "user":
                obj.id = user_id
            else:
                obj.id = assistant_id
            conversation.messages.append(obj)
        elif name == "MessageCitation":
            stored["citations"].append(obj)

    session.add = _add_side_effect  # type: ignore[method-assign]

    settings = MagicMock()
    settings.answering_prompt_version = "answering-v1"
    settings.generation_model = "fake-model"
    settings.generation_backend = "stub"
    settings.qa_min_rrf_score = 0.01
    settings.qa_max_context_chunks = 8
    settings.qa_context_token_budget = 1800

    with (
        patch.object(qa_service, "get_conversation", _fake_get_conversation),
        patch.object(qa_service, "assemble_context", return_value=hits),
        patch.object(qa_service, "evidence_is_sufficient", return_value=bool(hits)),
        patch.object(qa_service, "get_generator", return_value=_FakeGenerator(generation)),
    ):
        turn = qa_service.post_user_message(
            session,  # type: ignore[arg-type]
            conversation_id,
            question="What shall the system accept?",
            settings=settings,
        )
    return SimpleNamespace(turn=turn, persisted_citations=stored["citations"])


def test_valid_answer_with_valid_citations_is_completed() -> None:
    chunk = uuid.uuid4()
    result = _run_turn(
        hits=[_hit(chunk)],
        generation=GenerationResult(
            content="The system shall accept Markdown uploads.",
            citations=[CitationDraft(chunk_id=chunk, claim_index=0, source_quote="shall accept")],
            insufficient_evidence=False,
            model="fake",
            prompt_version="answering-v1",
        ),
    )
    turn = result.turn
    assert turn.status == "completed"
    assert turn.generation_status == "succeeded"
    assert turn.citation_chunk_ids == [str(chunk)]
    assert set(turn.citation_chunk_ids).issubset(set(turn.retrieved_chunk_ids))
    assert result.persisted_citations


def test_no_citations_is_insufficient_evidence() -> None:
    chunk = uuid.uuid4()
    result = _run_turn(
        hits=[_hit(chunk)],
        generation=GenerationResult(
            content="Sure, it accepts everything.",
            citations=[],
            insufficient_evidence=False,
            model="fake",
            prompt_version="answering-v1",
        ),
    )
    turn = result.turn
    assert turn.status == "insufficient_evidence"
    assert turn.generation_status == "insufficient_evidence"
    assert turn.citation_chunk_ids == []
    assert result.persisted_citations == []
    assert "Insufficient evidence" in turn.content


def test_only_forged_citations_is_insufficient_evidence_regression() -> None:
    """Regression: old code marked COMPLETED when retrieval hit but all cites forged."""
    retrieved = uuid.uuid4()
    forged = uuid.uuid4()
    result = _run_turn(
        hits=[_hit(retrieved)],
        generation=GenerationResult(
            content="Unsupported claim with a fake citation.",
            citations=[CitationDraft(chunk_id=forged, claim_index=0, source_quote="fake")],
            insufficient_evidence=False,
            model="fake",
            prompt_version="answering-v1",
        ),
    )
    turn = result.turn
    # This assertion fails under the pre-fix branch behavior.
    assert turn.status == "insufficient_evidence"
    assert turn.citation_chunk_ids == []
    assert result.persisted_citations == []
    assert str(forged) not in turn.content


def test_mixed_valid_and_forged_keeps_only_valid_and_completes() -> None:
    good = uuid.uuid4()
    forged = uuid.uuid4()
    result = _run_turn(
        hits=[_hit(good)],
        generation=GenerationResult(
            content="Grounded claim.",
            citations=[
                CitationDraft(chunk_id=good, claim_index=0, source_quote="ok"),
                CitationDraft(chunk_id=forged, claim_index=1, source_quote="nope"),
            ],
            insufficient_evidence=False,
            model="fake",
            prompt_version="answering-v1",
        ),
    )
    turn = result.turn
    assert turn.status == "completed"
    assert turn.citation_chunk_ids == [str(good)]
    assert str(forged) not in turn.citation_chunk_ids
    persisted_ids = {str(c.chunk_id) for c in result.persisted_citations}
    assert persisted_ids == {str(good)}


def test_generator_abstains_is_insufficient_evidence() -> None:
    chunk = uuid.uuid4()
    result = _run_turn(
        hits=[_hit(chunk)],
        generation=GenerationResult(
            content="I cannot answer from the provided excerpts.",
            citations=[],
            insufficient_evidence=True,
            model="fake",
            prompt_version="answering-v1",
        ),
    )
    turn = result.turn
    assert turn.status == "insufficient_evidence"
    assert turn.generation_status == "insufficient_evidence"
    assert turn.citation_chunk_ids == []
    assert "cannot answer" in turn.content.lower()


def test_retrieval_empty_is_insufficient_evidence() -> None:
    from app.qa import service as qa_service

    conversation_id = uuid.uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        workspace_id=uuid.uuid4(),
        title="New conversation",
        messages=[],
    )

    class _Session:
        def add(self, obj: Any) -> None:
            if obj.__class__.__name__ == "Message":
                obj.id = uuid.uuid4()
                conversation.messages.append(obj)

        def flush(self) -> None:
            return None

        def commit(self) -> None:
            return None

    settings = MagicMock()
    settings.answering_prompt_version = "answering-v1"
    settings.generation_model = "fake-model"
    settings.generation_backend = "stub"
    settings.qa_min_rrf_score = 0.01

    with (
        patch.object(qa_service, "get_conversation", return_value=conversation),
        patch.object(qa_service, "assemble_context", return_value=[]),
    ):
        turn = qa_service.post_user_message(
            _Session(),  # type: ignore[arg-type]
            conversation_id,
            question="Anything?",
            settings=settings,
        )
    assert turn.status == "insufficient_evidence"
    assert turn.retrieval_status == "empty"
    assert turn.generation_status == "skipped"
    assert turn.citation_chunk_ids == []


def test_completed_answers_always_have_valid_citation_invariant() -> None:
    """Property: completed ⇒ ≥1 citation ⊆ retrieved allow-list."""
    cases = [
        (uuid.uuid4(), True),
        (uuid.uuid4(), False),
    ]
    for chunk, include_cite in cases:
        cites = (
            [CitationDraft(chunk_id=chunk, claim_index=0, source_quote="q")] if include_cite else []
        )
        result = _run_turn(
            hits=[_hit(chunk)],
            generation=GenerationResult(
                content="Answer text",
                citations=cites,
                insufficient_evidence=False,
                model="fake",
                prompt_version="answering-v1",
            ),
        )
        turn = result.turn
        if turn.status == "completed":
            assert turn.citation_chunk_ids
            assert set(turn.citation_chunk_ids).issubset(set(turn.retrieved_chunk_ids))
        else:
            assert turn.status == "insufficient_evidence"
            assert turn.citation_chunk_ids == []
