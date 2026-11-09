"""Smoke test that make-eval equivalent produces reports."""

from __future__ import annotations

from pathlib import Path

from evals.harness.runner import run_eval

ROOT = Path(__file__).resolve().parents[2]


def test_run_eval_writes_reports(tmp_path: Path) -> None:
    out = tmp_path / "eval"
    report = run_eval(out_dir=out, enforce=False)
    assert (out / "report.json").exists()
    assert (out / "report.html").exists()
    assert report["exit_criteria"]["questions_ge_50"] is True
    assert report["exit_criteria"]["extraction_ge_20"] is True
    assert "retrieval_recall_at_10" in report["metrics"]
    assert "baseline_diff" in report
