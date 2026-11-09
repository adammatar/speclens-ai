import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listDocuments } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { DocumentSummary } from "../lib/types";

export function DocumentsPage() {
  const { apiKey } = useAuth();
  const [rows, setRows] = useState<DocumentSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!apiKey) return;
    listDocuments(apiKey)
      .then(setRows)
      .catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, [apiKey]);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Documents</h1>
          <p>Library of uploaded specifications in the default workspace.</p>
        </div>
        <Link className="btn amber" to="/documents/upload">
          Upload document
        </Link>
      </div>
      {error ? <div className="error">{error}</div> : null}
      <div className="list">
        {rows.length === 0 ? (
          <p className="muted">No documents yet.</p>
        ) : (
          rows.map((row) => (
            <Link key={row.id} className="list-item" to={`/documents/${row.id}`}>
              <div>
                <strong>{row.title}</strong>
                <div className="muted">
                  {row.version_count} version{row.version_count === 1 ? "" : "s"}
                </div>
              </div>
              <span className={`badge ${row.latest_status === "ready" ? "ok" : "warn"}`}>
                {row.latest_status ?? "unknown"}
              </span>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
