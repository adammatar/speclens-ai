"""Unit tests for eval metrics and graders."""

from __future__ import annotations

from evals.harness.graders import grade_extraction, grade_qa_citations, grade_retrieval
from evals.harness.metrics import f1_score, mean_reciprocal_rank, recall_at_k


def test_recall_at_k_and_mrr() -> None:
    ranked = ["a", "b", "c"]
    relevant = {"c", "x"}
    assert recall_at_k(ranked, relevant, 10) == 0.5
    assert mean_reciprocal_rank(ranked, {"b"}) == 0.5


def test_f1_and_extraction_grader() -> None:
    assert f1_score({"a", "b"}, {"a", "b"}) == 1.0
    result = grade_extraction(
        [
            {
                "gold_statements": ["The system shall A."],
                "predicted_statements": ["The system shall A."],
            }
        ]
    )
    assert result["extraction_f1"] == 1.0


def test_citation_grader_zero_unsupported() -> None:
    result = grade_qa_citations(
        [
            {
                "allowlisted_chunk_ids": ["1", "2"],
                "gold_citation_ids": ["1"],
                "predicted_citation_ids": ["1"],
            }
        ]
    )
    assert result["unsupported_claim_rate"] == 0.0
    assert result["citation_precision"] == 1.0


def test_retrieval_grader() -> None:
    result = grade_retrieval(
        [
            {
                "relevant_chunk_ids": ["r1"],
                "predicted_ranked_ids": ["r1", "x"],
            }
        ]
    )
    assert result["retrieval_recall_at_10"] == 1.0
