"""Stub embedder determinism tests."""

from __future__ import annotations

from app.embeddings.stub import StubEmbedder


def test_stub_embedder_is_deterministic_and_normalized() -> None:
    embedder = StubEmbedder(model_name="speclens-stub-v1", dims=256)
    a = embedder.embed_texts(["alpha bravo"])[0]
    b = embedder.embed_texts(["alpha bravo"])[0]
    c = embedder.embed_texts(["something else entirely"])[0]
    assert a == b
    assert a != c
    assert abs(sum(v * v for v in a) - 1.0) < 1e-6
