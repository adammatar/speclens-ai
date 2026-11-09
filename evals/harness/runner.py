"""Evaluation runner: load datasets, grade, write reports."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.harness import graders
from evals.harness.report import (
    apply_thresholds,
    baseline_diff,
    write_html_report,
    write_json_report,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASETS = ROOT / "evals" / "datasets"
DEFAULT_THRESHOLDS = ROOT / "evals" / "thresholds.json"
DEFAULT_BASELINE = ROOT / "evals" / "baselines" / "baseline_v1.json"
DEFAULT_OUT = ROOT / "artifacts" / "eval"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def run_eval(
    *,
    datasets_dir: Path = DEFAULT_DATASETS,
    thresholds_path: Path = DEFAULT_THRESHOLDS,
    baseline_path: Path | None = DEFAULT_BASELINE,
    out_dir: Path = DEFAULT_OUT,
    enforce: bool = False,
) -> dict[str, Any]:
    thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
    baseline = None
    if baseline_path and baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    suites = {
        "retrieval": (datasets_dir / "retrieval_v1.jsonl", graders.grade_retrieval),
        "qa_citations": (datasets_dir / "qa_citations_v1.jsonl", graders.grade_qa_citations),
        "extraction": (datasets_dir / "extraction_v1.jsonl", graders.grade_extraction),
        "compare": (datasets_dir / "compare_v1.jsonl", graders.grade_compare),
        "insufficient_evidence": (
            datasets_dir / "insufficient_evidence_v1.jsonl",
            graders.grade_insufficient_evidence,
        ),
        "injection": (datasets_dir / "injection_v1.jsonl", graders.grade_injection),
    }

    metrics: dict[str, float] = {}
    dataset_counts: dict[str, int] = {}
    suite_results: dict[str, Any] = {}

    for name, (path, grader) in suites.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing dataset: {path}")
        rows = load_jsonl(path)
        dataset_counts[name] = len(rows)
        result = grader(rows)
        suite_results[name] = result
        for key, value in result.items():
            if key == "n":
                metrics[f"{name}_n"] = value
            else:
                metrics[key] = value

    question_count = dataset_counts.get("retrieval", 0) + dataset_counts.get("qa_citations", 0)
    extraction_count = dataset_counts.get("extraction", 0)

    gates = apply_thresholds(metrics, thresholds)
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "offline-stub",
        "enforce": enforce,
        "advisory": bool(thresholds.get("advisory", True)) and not enforce,
        "dataset_counts": dataset_counts,
        "question_like_count": question_count,
        "extraction_count": extraction_count,
        "metrics": metrics,
        "gates": gates,
        "suite_results": suite_results,
        "baseline_diff": baseline_diff(metrics, baseline),
        "exit_criteria": {
            "questions_ge_50": question_count >= 50,
            "extraction_ge_20": extraction_count >= 20,
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = ROOT / "evals" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    write_json_report(out_dir / "report.json", report)
    write_html_report(out_dir / "report.html", report)
    write_json_report(reports_dir / "latest.json", report)
    write_html_report(reports_dir / "latest.html", report)

    failures = [name for name, gate in gates.items() if gate.get("status") == "fail"]
    report["failed_gates"] = failures
    write_json_report(out_dir / "report.json", report)

    if enforce and failures:
        print(f"EVAL ENFORCE failed gates: {failures}", file=sys.stderr)
        raise SystemExit(2)
    if failures:
        print(f"EVAL advisory failed gates (not blocking): {failures}")
    else:
        print("EVAL all gates passed")
    print(f"Wrote {out_dir / 'report.json'} and {out_dir / 'report.html'}")
    return report
