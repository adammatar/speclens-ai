import { useEffect, useState } from "react";
import { getMeta } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { MetaInfo } from "../lib/types";

export function SettingsPage() {
  const { apiKey } = useAuth();
  const [meta, setMeta] = useState<MetaInfo | null>(null);

  useEffect(() => {
    getMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  return (
    <div className="main-pad stack" style={{ maxWidth: 640 }}>
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p>Workspace session and runtime backends.</p>
        </div>
      </div>
      <div className="version-card" style={{ display: "block" }}>
        <div className="field">
          <label>Session API key</label>
          <input readOnly value={apiKey ? "••••••••••••••••" : ""} />
        </div>
        <p className="muted" style={{ marginTop: "0.75rem", fontSize: "0.85rem" }}>
          Stored in sessionStorage only. Sign out clears it.
        </p>
      </div>
      <div className="version-card" style={{ display: "block" }}>
        <strong>Runtime</strong>
        <p className="muted" style={{ marginTop: 8, fontSize: "0.9rem" }}>
          Version {meta?.version ?? "…"} · mode {meta?.deployment_mode ?? "…"}
          <br />
          Embeddings {meta?.embedding_backend ?? "…"} · Generation{" "}
          {meta?.generation_backend ?? "…"} · Extraction {meta?.extraction_backend ?? "…"}
          <br />
          Retention {meta?.retention_days ?? "—"} days · Auth{" "}
          {meta?.auth_required ? "required" : "open"}
        </p>
      </div>
    </div>
  );
}
