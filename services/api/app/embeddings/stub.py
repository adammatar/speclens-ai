"""Deterministic local embedder for CI and local mode (no external API)."""

from __future__ import annotations

import hashlib
import math
import re

# Unicode word tokens so Hebrew/Arabic/CJK script chunks embed usefully in stub mode.
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class StubEmbedder:
    """Hash-bag embedder: stable vectors for identical text, useful for hybrid search tests."""

    def __init__(self, *, model_name: str, dims: int) -> None:
        if dims <= 0:
            raise ValueError("dims must be positive")
        self._model_name = model_name
        self._dims = dims

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dims(self) -> int:
        return self._dims

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self._dims
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            tokens = ["empty"]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            # Use two bytes to pick index and a signed contribution.
            index = int.from_bytes(digest[0:2], "big") % self._dims
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            weight = 1.0 + (digest[3] / 255.0)
            vec[index] += sign * weight
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
