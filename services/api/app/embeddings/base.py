"""Embedder protocol."""

from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    """Produces fixed-dimension vectors for text batches."""

    @property
    def model_name(self) -> str: ...

    @property
    def dims(self) -> int: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one L2-oriented vector per input text."""
