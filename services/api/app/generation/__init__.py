"""Answer generation backends for cited QA."""

from app.generation.base import CitationDraft, GenerationResult
from app.generation.factory import get_generator

__all__ = ["CitationDraft", "GenerationResult", "get_generator"]
