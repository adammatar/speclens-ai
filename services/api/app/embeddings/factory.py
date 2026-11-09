"""Embedder factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.embeddings.base import Embedder
from app.embeddings.openai_backend import OpenAIEmbedder
from app.embeddings.stub import StubEmbedder


def get_embedder(settings: Settings | None = None) -> Embedder:
    cfg = settings or get_settings()
    if cfg.embedding_backend == "stub":
        return StubEmbedder(model_name=cfg.embedding_model, dims=cfg.embedding_dims)
    if cfg.embedding_backend == "openai":
        return OpenAIEmbedder(cfg)
    raise ValueError(f"Unsupported embedding backend: {cfg.embedding_backend}")
