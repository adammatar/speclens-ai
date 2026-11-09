"""OpenAI embeddings backend (optional; unused unless API key configured)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.core.config import Settings


class OpenAIEmbedder:
    """Calls OpenAI / Gemini OpenAI-compatible embeddings HTTP API (no SDK)."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for openai embedding backend")
        self._api_key = settings.openai_api_key
        self._base_url = (settings.openai_base_url or "https://api.openai.com/v1").rstrip("/")
        self._model_name = settings.embedding_model
        self._dims = settings.embedding_dims
        self._settings = settings

    def _settings_send_dimensions(self) -> bool:
        return bool(getattr(self._settings, "embedding_send_dimensions", False))

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dims(self) -> int:
        return self._dims

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload: dict[str, object] = {
            "model": self._model_name,
            "input": texts,
        }
        # OpenAI text-embedding-3* accepts dimensions; Gemini/compat often does not.
        model_l = self._model_name.lower()
        if "text-embedding-3" in model_l or model_l.startswith("text-embedding-ada"):
            payload["dimensions"] = self._dims
        elif self._settings_send_dimensions():
            payload["dimensions"] = self._dims
        request = urllib.request.Request(
            f"{self._base_url}/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI embeddings request failed: {exc}") from exc

        data = sorted(body.get("data", []), key=lambda row: int(row.get("index", 0)))
        vectors = [list(map(float, row["embedding"])) for row in data]
        if len(vectors) != len(texts):
            raise RuntimeError("OpenAI embeddings response size mismatch")
        return vectors
