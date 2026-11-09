import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { listRequirements, startExtraction } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Requirement } from "../lib/types";

export function RequirementsPage() {
  const { apiKey } = useAuth();
  const [params] = useSearchParams();
  const version = params.get("version") || "";
  const [rows, setRows] = useState<Requirement[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [versionInput, setVersionInput] = useState(version);

  async function refresh(versionId?: string) {
    if (!apiKey) return;
    const data = await listRequirements(apiKey, versionId || undefined);
    setRows(data);
  }

  useEffect(() => {
    if (!apiKey) return;
    listRequirements(apiKey, version || undefined)
      .then(setRows)
      .catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, [apiKey, version]);

  async function onExtract() {
    if (!apiKey || !versionInput) return;
    setError(null);
    try {
      await startExtraction(apiKey, versionInput);
      // naive wait then refresh
      window.setTimeout(() => {
        refresh(versionInput).catch(() => undefined);
      }, 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extraction failed");
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Requirements</h1>
          <p>Structured extractions with review state and source quotes.</p>
        </div>
      </div>
      <div className="row">
        <div className="field" style={{ maxWidth: 420 }}>
          <label htmlFor="ver">Document version id</label>
          <input
            id="ver"
            value={versionInput}
            onChange={(e) => setVersionInput(e.target.value)}
            placeholder="UUID"
          />
        </div>
        <button className="btn" type="button" onClick={onExtract}>
          Run extraction
        </button>
        <button
          className="btn secondary"
          type="button"
          onClick={() => refresh(versionInput || undefined)}
        >
          Refresh
        </button>
      </div>
      {error ? <div className="error">{error}</div> : null}
      <div className="list">
        {rows.map((row) => (
          <div key={row.id} className="list-item" style={{ alignItems: "flex-start" }}>
            <div className="stack" style={{ gap: "0.35rem" }}>
              <strong>{row.statement}</strong>
              <span className="muted">
                {row.requirement_type} · {row.priority} · confidence{" "}
                {row.confidence.toFixed(2)}
              </span>
            </div>
            <span className="badge">{row.review_state}</span>
          </div>
        ))}
        {!rows.length ? <p className="muted">No requirements loaded.</p> : null}
      </div>
    </div>
  );
}
