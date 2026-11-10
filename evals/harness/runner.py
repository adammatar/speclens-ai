"""Evaluation runner: execute application pipelines, grade, write reports."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.harness import graders
from evals.harness.pipeline import (
    PREDICTORS,
    close_pipeline,
    database_available,
    open_pipeline,
    percentile,
)
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


def assert_no_prefilled_predictions(rows: list[dict[str, Any]], path: Path) -> None:
    for row in rows:
        bad = [k for k in row if str(k).startswith("predicted_")]
        if bad:
            raise ValueError(
                f"Gold dataset {path} contains prefilled predictions {bad}; "
                "remove them — the harness must generate predictions at runtime"
            )


def _git_commit() -> str | None:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            or None
        )
    except Exception:  # noqa: BLE001
        return None


def run_eval(
    *,
    datasets_dir: Path = DEFAULT_DATASETS,
    thresholds_path: Path = DEFAULT_THRESHOLDS,
    baseline_path: Path | None = DEFAULT_BASELINE,
    out_dir: Path = DEFAULT_OUT,
    enforce: bool = False,
    mode: str | None = None,
    retrieval_override: Any | None = None,
) -> dict[str, Any]:
    """Run evaluation.

    mode: ``stub`` (default, CI) or ``live`` (optional paid providers).
    retrieval_override: optional callable(ctx, row) -> row for regression tests.
    """
    resolved_mode = mode or os.getenv("EVAL_MODE", "stub")
    thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
    baseline = None
    if baseline_path and baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    if not database_available():
        msg = (
            "Postgres is required for real SpecLens evaluation "
            f"(DATABASE_URL={os.getenv('DATABASE_URL', 'default local')})"
        )
        if enforce:
            print(msg, file=sys.stderr)
            raise SystemExit(2)
        raise RuntimeError(msg)

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

    ctx = open_pipeline(mode=resolved_mode)
    metrics: dict[str, float] = {}
    dataset_counts: dict[str, int] = {}
    suite_results: dict[str, Any] = {}
    example_failures: list[dict[str, Any]] = []

    try:
        for name, (path, grader) in suites.items():
            if not path.exists():
                raise FileNotFoundError(f"Missing dataset: {path}")
            rows = load_jsonl(path)
            assert_no_prefilled_predictions(rows, path)
            dataset_counts[name] = len(rows)

            predictor = (
                retrieval_override
                if name == "retrieval" and retrieval_override
                else (PREDICTORS[name])
            )
            predicted_rows: list[dict[str, Any]] = []
            for row in rows:
                try:
                    predicted_rows.append(predictor(ctx, row))
                except Exception as exc:  # noqa: BLE001
                    example_failures.append({"suite": name, "id": row.get("id"), "error": str(exc)})
                    # Leave without predictions so graders score a miss.
                    predicted_rows.append(dict(row))

            result = grader(predicted_rows)
            suite_results[name] = result
            for key, value in result.items():
                if key == "n":
                    metrics[f"{name}_n"] = value
                else:
                    metrics[key] = value
    finally:
        latency_metrics = {
            "latency_p50_ms": percentile(ctx.latencies_ms, 50),
            "latency_p95_ms": percentile(ctx.latencies_ms, 95),
            "input_tokens": float(ctx.token_prompt),
            "output_tokens": float(ctx.token_completion),
            "estimated_cost_usd": 0.0,
        }
        backends = dict(ctx.backends)
        eval_mode = ctx.mode
        close_pipeline(ctx)

    metrics.update(latency_metrics)

    question_count = dataset_counts.get("retrieval", 0) + dataset_counts.get("qa_citations", 0)
    extraction_count = dataset_counts.get("extraction", 0)

    gates = apply_thresholds(metrics, thresholds)
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": eval_mode,
        "synthetic_stub_badge": eval_mode == "stub",
        "backends": backends,
        "prompt_versions": {
            "qa": "qa-v1",
            "extraction": "extraction-v1",
        },
        "embedding": {
            "backend": backends.get("embedding"),
            "model": backends.get("embedding_model"),
            "dims": 256,
        },
        "dataset_version": "v1-runtime",
        "git_commit": _git_commit(),
        "enforce": enforce,
        "advisory": bool(thresholds.get("advisory", False)) and not enforce,
        "dataset_counts": dataset_counts,
        "question_like_count": question_count,
        "extraction_count": extraction_count,
        "metrics": metrics,
        "gates": gates,
        "suite_results": suite_results,
        "example_failures": example_failures,
        "baseline_diff": baseline_diff(metrics, baseline),
        "exit_criteria": {
            "questions_ge_50": question_count >= 50,
            "extraction_ge_20": extraction_count >= 20,
        },
        "caveat": (
            "Stub/synthetic results measure deterministic backend behavior on synthetic "
            "fixtures; they are not production accuracy claims."
            if eval_mode == "stub"
            else "Live-provider results depend on configured models and may vary."
        ),
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
    write_json_report(reports_dir / "latest.json", report)

    if enforce and failures:
        print(f"EVAL ENFORCE failed gates: {failures}", file=sys.stderr)
        raise SystemExit(2)
    if example_failures:
        print(f"EVAL example failures: {len(example_failures)}")
    if failures:
        print(f"EVAL failed gates: {failures}")
    else:
        print("EVAL all gates passed")
    print(f"Wrote {out_dir / 'report.json'} and {out_dir / 'report.html'}")
    return report
