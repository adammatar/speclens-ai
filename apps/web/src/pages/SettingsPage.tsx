import { useEffect, useState } from "react";
import { getMeta } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { MetaInfo } from "../lib/types";

export function SettingsPage() {
  const { apiKey, signOut } = useAuth();
  const [meta, setMeta] = useState<MetaInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMeta()
      .then(setMeta)
      .catch((err) => setError(err instanceof Error ? err.message : "Meta load failed"));
  }, []);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p>Retention and deployment metadata — no secrets in this panel.</p>
        </div>
      </div>
      {error ? <div className="error">{error}</div> : null}
      <div className="metrics">
        <div className="metric">
          <strong>{meta?.version ?? "—"}</strong>
          <span className="muted">API version</span>
        </div>
        <div className="metric">
          <strong>{meta?.retention_days ?? "—"}</strong>
          <span className="muted">Retention days</span>
        </div>
        <div className="metric">
          <strong>{meta?.deployment_mode ?? "—"}</strong>
          <span className="muted">Deployment mode</span>
        </div>
        <div className="metric">
          <strong>{meta?.auth_required ? "on" : "off"}</strong>
          <span className="muted">Auth required</span>
        </div>
      </div>
      <p className="muted">
        API key present: {apiKey ? "yes (sessionStorage)" : "no"}. OpenAI keys never ship in
        this bundle.
      </p>
      <button className="btn secondary" type="button" onClick={signOut}>
        Clear session key
      </button>
    </div>
  );
}
