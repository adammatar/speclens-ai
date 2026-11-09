"""Unit tests for OpenAI-compatible (Gemini) chat generator."""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.generation.openai_compat import OpenAICompatGenerator, _extract_chat_text
from app.retrieval.search import SearchHit


def _hit(text: str) -> SearchHit:
    cid = uuid.uuid4()
    return SearchHit(
        chunk_id=cid,
        document_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        heading_path="Page 2",
        page_number=2,
        excerpt=text,
        start_offset=0,
        end_offset=len(text),
        rrf_score=0.5,
    )


def test_extract_chat_text_plain_message() -> None:
    body: dict[str, Any] = {
        "choices": [{"message": {"role": "assistant", "content": '{"answer":"ok"}'}}]
    }
    assert _extract_chat_text(body) == '{"answer":"ok"}'


def test_openai_compat_generate_parses_gemini_style_json() -> None:
    hit = _hit("John was born on 15 March 2000 in the vital record section.")
    settings = Settings(
        openai_api_key="test-gemini-key",
        openai_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        generation_backend="openai_compat",
        generation_model="gemini-3.8-flash",
    )
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "answer": "John was born on 15 March 2000.",
                            "insufficient_evidence": False,
                            "citations": [
                                {
                                    "chunk_id": str(hit.chunk_id),
                                    "source_quote": "born on 15 March 2000",
                                }
                            ],
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8},
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp) as mocked:
        result = OpenAICompatGenerator(settings).generate(
            question="When was John born?",
            hits=[hit],
            allowlisted_chunk_ids={hit.chunk_id},
            prompt_version="answering-v1",
        )

    assert "15 March 2000" in result.content
    assert result.insufficient_evidence is False
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == hit.chunk_id
    called_url = mocked.call_args[0][0].full_url
    assert called_url.endswith("/chat/completions")


def test_factory_selects_openai_compat() -> None:
    from app.generation.factory import get_generator

    settings = Settings(
        openai_api_key="k",
        openai_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        generation_backend="openai_compat",
        generation_model="gemini-3.8-flash",
    )
    gen = get_generator(settings)
    assert isinstance(gen, OpenAICompatGenerator)
