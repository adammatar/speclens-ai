"""Smoke + regression tests for the real evaluation harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from evals.harness.pipeline import database_available
from evals.harness.runner import assert_no_prefilled_predictions, load_jsonl, run_eval

ROOT = Path(__file__).resolve().parents[2]
DATASETS = ROOT / "evals" / "datasets"

pytestmark = pytest.mark.skipif(
    not database_available(),
    reason="Postgres required for real evaluation harness",
)


def test_gold_datasets_have_no_prefilled_predictions() -> None:
    for path in DATASETS.glob("*.jsonl"):
        rows = load_jsonl(path)
        assert_no_prefilled_predictions(rows, path)


def test_run_eval_writes_reports(tmp_path: Path) -> None:
    out = tmp_path / "eval"
    report = run_eval(out_dir=out, enforce=False, mode="stub", baseline_path=None)
    assert (out / "report.json").exists()
    assert (out / "report.html").exists()
    assert report["mode"] == "stub"
    assert report["synthetic_stub_badge"] is True
    assert report["exit_criteria"]["questions_ge_50"] is True
    assert report["exit_criteria"]["extraction_ge_20"] is True
    assert "retrieval_recall_at_10" in report["metrics"]
    assert "retrieval_recall_at_5" in report["metrics"]
    assert "latency_p50_ms" in report["metrics"]
    # Predictions came from the pipeline — report must not pretend offline fixtures.
    assert report["mode"] != "offline-stub"
    html = (out / "report.html").read_text(encoding="utf-8")
    assert "SYNTHETIC / STUB" in html


def test_bad_retrieval_drops_metric_and_fails_threshold(tmp_path: Path) -> None:
    """Deliberately broken retrieval must move metrics and fail enforcement."""

    def bad_retrieval(_ctx: Any, row: dict[str, Any]) -> dict[str, Any]:
        return {**row, "predicted_ranked_ids": ["not-a-real-gold-id"]}

    out = tmp_path / "eval-bad"
    with pytest.raises(SystemExit) as exc:
        run_eval(
            out_dir=out,
            enforce=True,
            mode="stub",
            baseline_path=None,
            retrieval_override=bad_retrieval,
        )
    assert exc.value.code == 2
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["metrics"]["retrieval_recall_at_10"] < 0.5
    assert "retrieval_recall_at_10" in report.get("failed_gates", [])
