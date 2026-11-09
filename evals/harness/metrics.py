"""Core metric helpers."""

from __future__ import annotations


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 1.0
    top = ranked_ids[:k]
    hits = sum(1 for item in top if item in relevant_ids)
    return hits / len(relevant_ids)


def mean_reciprocal_rank(ranked_ids: list[str], relevant_ids: set[str]) -> float:
    if not relevant_ids:
        return 1.0
    for index, item in enumerate(ranked_ids, start=1):
        if item in relevant_ids:
            return 1.0 / index
    return 0.0


def precision(predicted: set[str], gold: set[str]) -> float:
    if not predicted:
        return 1.0 if not gold else 0.0
    return len(predicted & gold) / len(predicted)


def recall(predicted: set[str], gold: set[str]) -> float:
    if not gold:
        return 1.0
    return len(predicted & gold) / len(gold)


def f1_score(predicted: set[str], gold: set[str]) -> float:
    p = precision(predicted, gold)
    r = recall(predicted, gold)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
