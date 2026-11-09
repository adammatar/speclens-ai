"""Extractor factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.extraction.base import RequirementExtractor
from app.extraction.openai_backend import OpenAIRequirementExtractor
from app.extraction.stub import StubRequirementExtractor


def get_extractor(settings: Settings | None = None) -> RequirementExtractor:
    cfg = settings or get_settings()
    if cfg.extraction_backend == "stub":
        return StubRequirementExtractor()
    if cfg.extraction_backend == "openai":
        return OpenAIRequirementExtractor(cfg)
    raise ValueError(f"Unsupported extraction backend: {cfg.extraction_backend}")
