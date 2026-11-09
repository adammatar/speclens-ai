"""Requirement alignment helpers (stub-first similarity)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.db.models import ChangeCategory, Requirement

_TOKEN = re.compile(r"[a-z0-9]+")
_MODAL_DOWNGRADE = re.compile(r"\bshall\b|\bmust\b", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class AlignmentPair:
    base: Requirement | None
    target: Requirement | None
    similarity: float
    category: ChangeCategory


def normalize_statement(text: str) -> str:
    tokens = _TOKEN.findall(text.lower())
    return " ".join(tokens)


def statement_similarity(a: str, b: str) -> float:
    na = normalize_statement(a)
    nb = normalize_statement(b)
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta = set(na.split())
    tb = set(nb.split())
    jaccard = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    return 0.6 * seq + 0.4 * jaccard


def source_quote(requirement: Requirement) -> str | None:
    for source in requirement.sources or []:
        if isinstance(source, dict):
            quote = str(source.get("source_quote") or "").strip()
            if quote:
                return quote
    return None


def classify_pair(
    base: Requirement | None,
    target: Requirement | None,
    *,
    similarity: float,
    match_threshold: float = 0.72,
    clarify_threshold: float = 0.9,
) -> ChangeCategory:
    if base is None and target is not None:
        return ChangeCategory.ADDED
    if base is not None and target is None:
        return ChangeCategory.REMOVED
    assert base is not None and target is not None
    if similarity < match_threshold:
        return ChangeCategory.UNCERTAIN

    if base.priority != target.priority and normalize_statement(
        base.statement
    ) == normalize_statement(target.statement):
        return ChangeCategory.PRIORITY_CHANGED

    base_ac = _criteria_text(base)
    target_ac = _criteria_text(target)
    if base_ac != target_ac and normalize_statement(base.statement) == normalize_statement(
        target.statement
    ):
        return ChangeCategory.ACCEPTANCE_CRITERIA_CHANGED

    if _is_potential_breaking(base.statement, target.statement):
        return ChangeCategory.POTENTIAL_BREAKING_CHANGE

    if similarity >= clarify_threshold and normalize_statement(
        base.statement
    ) != normalize_statement(target.statement):
        return ChangeCategory.CLARIFIED

    if similarity >= match_threshold and normalize_statement(base.statement) != normalize_statement(
        target.statement
    ):
        return ChangeCategory.BEHAVIOR_CHANGED

    if normalize_statement(base.statement) == normalize_statement(target.statement):
        # Identical after normalize - still emit clarified only if soft differences exist.
        if base.statement.strip() != target.statement.strip():
            return ChangeCategory.CLARIFIED
        return ChangeCategory.CLARIFIED

    return ChangeCategory.UNCERTAIN


def align_requirements(
    base_rows: list[Requirement],
    target_rows: list[Requirement],
    *,
    match_threshold: float = 0.72,
) -> list[AlignmentPair]:
    """Greedy alignment: external_id first, then best unused similarity."""
    pairs: list[AlignmentPair] = []
    used_target: set[object] = set()

    # external_id exact matches
    target_by_ext = {
        row.external_id: row for row in target_rows if row.external_id and row.external_id.strip()
    }
    remaining_base: list[Requirement] = []
    for base in base_rows:
        if base.external_id and base.external_id in target_by_ext:
            target = target_by_ext[base.external_id]
            if id(target) in used_target:
                remaining_base.append(base)
                continue
            sim = statement_similarity(base.statement, target.statement)
            category = classify_pair(base, target, similarity=max(sim, match_threshold))
            pairs.append(AlignmentPair(base=base, target=target, similarity=sim, category=category))
            used_target.add(id(target))
        else:
            remaining_base.append(base)

    remaining_target = [row for row in target_rows if id(row) not in used_target]

    # Similarity matching
    candidates: list[tuple[float, Requirement, Requirement]] = []
    for base in remaining_base:
        for target in remaining_target:
            sim = statement_similarity(base.statement, target.statement)
            if sim >= match_threshold:
                candidates.append((sim, base, target))
    candidates.sort(key=lambda item: item[0], reverse=True)

    matched_base: set[object] = set()
    for sim, base, target in candidates:
        if id(base) in matched_base or id(target) in used_target:
            continue
        category = classify_pair(base, target, similarity=sim)
        pairs.append(AlignmentPair(base=base, target=target, similarity=sim, category=category))
        matched_base.add(id(base))
        used_target.add(id(target))

    for base in remaining_base:
        if id(base) not in matched_base:
            pairs.append(
                AlignmentPair(
                    base=base,
                    target=None,
                    similarity=0.0,
                    category=ChangeCategory.REMOVED,
                )
            )
    for target in remaining_target:
        if id(target) not in used_target:
            pairs.append(
                AlignmentPair(
                    base=None,
                    target=target,
                    similarity=0.0,
                    category=ChangeCategory.ADDED,
                )
            )
    return pairs


def _criteria_text(requirement: Requirement) -> str:
    parts: list[str] = []
    for item in requirement.acceptance_criteria or []:
        if isinstance(item, dict):
            parts.append(str(item.get("statement") or "").strip().lower())
        else:
            parts.append(str(item).strip().lower())
    return "|".join(sorted(parts))


def _is_potential_breaking(old: str, new: str) -> bool:
    old_l = old.lower()
    new_l = new.lower()
    if _MODAL_DOWNGRADE.search(old_l) and re.search(r"\b(should|may|optional)\b", new_l):
        return True
    if "must not" in new_l and "must not" not in old_l:
        return True
    return "breaking" in new_l
