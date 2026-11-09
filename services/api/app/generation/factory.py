"""Generator factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.generation.base import Generator
from app.generation.openai_backend import OpenAIGenerator
from app.generation.openai_compat import OpenAICompatGenerator
from app.generation.stub import StubGenerator


def get_generator(settings: Settings | None = None) -> Generator:
    cfg = settings or get_settings()
    if cfg.generation_backend == "stub":
        return StubGenerator(model_name=cfg.generation_model)
    if cfg.generation_backend == "openai":
        return OpenAIGenerator(cfg)
    if cfg.generation_backend == "openai_compat":
        return OpenAICompatGenerator(cfg)
    raise ValueError(f"Unsupported generation backend: {cfg.generation_backend}")
