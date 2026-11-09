export function EvaluationPage() {
  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Evaluation</h1>
          <p>
            Offline graders stay in Python (`make eval`). This page is the operator
            entry point for thresholds and reports.
          </p>
        </div>
      </div>
      <div className="stack">
        <p>
          Run the harness from the repo root:
        </p>
        <pre className="prose" style={{ margin: 0 }}>
{`make eval
# or enforce gates
python -m evals.harness --enforce`}
        </pre>
        <p className="muted">
          Reports write to `artifacts/eval/report.json` and `report.html`. Suites cover
          retrieval, citations, extraction, compare, insufficient evidence, and prompt
          injection.
        </p>
      </div>
    </div>
  );
}
