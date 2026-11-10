"""JSON + HTML report writers and baseline diff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_html_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = report.get("metrics", {})
    gates = report.get("gates", {})
    baseline_diff = report.get("baseline_diff", {})
    rows = ["<tr><th>Metric</th><th>Value</th><th>Threshold</th><th>Status</th></tr>"]
    for name, value in sorted(metrics.items()):
        if name.endswith("_n") or name == "n":
            continue
        gate = gates.get(name, {})
        status = gate.get("status", "n/a")
        threshold = gate.get("threshold", "")
        rows.append(
            f"<tr><td>{name}</td><td>{value:.4f}</td><td>{threshold}</td><td>{status}</td></tr>"
        )
    diff_rows = ["<tr><th>Metric</th><th>Current</th><th>Baseline</th><th>Delta</th></tr>"]
    for name, item in sorted(baseline_diff.items()):
        diff_rows.append(
            "<tr>"
            f"<td>{name}</td>"
            f"<td>{item.get('current', 0):.4f}</td>"
            f"<td>{item.get('baseline', 0):.4f}</td>"
            f"<td>{item.get('delta', 0):+.4f}</td>"
            "</tr>"
        )
    badge = (
        "SYNTHETIC / STUB — not production accuracy"
        if report.get("synthetic_stub_badge")
        else "Live provider evaluation"
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>SpecLens Eval Report</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; color: #122; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; }}
    th, td {{ border: 1px solid #ccd; padding: 0.4rem 0.6rem; text-align: left; }}
    th {{ background: #eef3f8; }}
    .pass {{ color: #0a7; }}
    .fail {{ color: #c22; }}
    .advisory {{ color: #a60; }}
  </style>
</head>
<body>
  <h1>SpecLens evaluation report</h1>
  <p>Generated: {report.get("generated_at", "")}</p>
  <p>Mode: {report.get("mode", "stub")} | Enforce: {report.get("enforce", False)}
     | Commit: {report.get("git_commit", "n/a")}</p>
  <p><strong>{badge}</strong></p>
  <p>{report.get("caveat", "")}</p>
  <h2>Backends</h2>
  <pre>{json.dumps(report.get("backends", {}), indent=2)}</pre>
  <h2>Dataset counts</h2>
  <pre>{json.dumps(report.get("dataset_counts", {}), indent=2)}</pre>
  <h2>Example failures</h2>
  <pre>{json.dumps(report.get("example_failures", []), indent=2)}</pre>
  <h2>Metrics</h2>
  <table>
    {"".join(rows)}
  </table>
  <h2>Baseline comparison</h2>
  <table>
    {"".join(diff_rows)}
  </table>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def apply_thresholds(
    metrics: dict[str, float],
    thresholds: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    gates: dict[str, dict[str, Any]] = {}
    rules = thresholds.get("metrics", {})
    for name, rule in rules.items():
        value = float(metrics.get(name, 0.0))
        status = "pass"
        threshold_desc = ""
        if "min" in rule:
            threshold_desc = f">= {rule['min']}"
            if value < float(rule["min"]):
                status = "fail"
        if "max" in rule:
            threshold_desc = threshold_desc if threshold_desc else f"<= {rule['max']}"
            if value > float(rule["max"]):
                status = "fail"
        gates[name] = {"status": status, "value": value, "threshold": threshold_desc}
    return gates


def baseline_diff(
    current: dict[str, float],
    baseline: dict[str, Any] | None,
) -> dict[str, dict[str, float]]:
    if not baseline:
        return {}
    base_metrics = baseline.get("metrics", baseline)
    out: dict[str, dict[str, float]] = {}
    for name, value in current.items():
        if name.endswith("_n") or name == "n":
            continue
        if name not in base_metrics:
            continue
        base_val = float(base_metrics[name])
        out[name] = {
            "current": float(value),
            "baseline": base_val,
            "delta": float(value) - base_val,
        }
    return out
