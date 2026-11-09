import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHealth, getMeta, listConversations, listDocuments } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { MetaInfo } from "../lib/types";

export function DashboardPage() {
  const { apiKey } = useAuth();
  const [docs, setDocs] = useState(0);
  const [chats, setChats] = useState(0);
  const [health, setHealth] = useState("…");
  const [meta, setMeta] = useState<MetaInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!apiKey) return;
    let cancelled = false;
    (async () => {
      try {
        const [d, c, h, m] = await Promise.all([
          listDocuments(apiKey),
          listConversations(apiKey),
          getHealth(),
          getMeta(),
        ]);
        if (cancelled) return;
        setDocs(d.length);
        setChats(c.length);
        setHealth(h.status);
        setMeta(m);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiKey]);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Workspace</h1>
          <p>Default workspace overview for SpecLens local / demo deployments.</p>
        </div>
        <div className="row">
          <Link className="btn" to="/documents/upload">
            Upload
          </Link>
          <Link className="btn secondary" to="/chat">
            Ask
          </Link>
        </div>
      </div>
      {error ? <div className="error">{error}</div> : null}
      <div className="metrics">
        <div className="metric">
          <strong>{docs}</strong>
          <span className="muted">Documents</span>
        </div>
        <div className="metric">
          <strong>{chats}</strong>
          <span className="muted">Conversations</span>
        </div>
        <div className="metric">
          <strong>{health}</strong>
          <span className="muted">API health</span>
        </div>
        <div className="metric">
          <strong>{meta?.retention_days ?? "—"}</strong>
          <span className="muted">Retention days</span>
        </div>
      </div>
      <p className="muted">
        Mode {meta?.deployment_mode ?? "…"} · backends {meta?.embedding_backend}/
        {meta?.generation_backend}/{meta?.extraction_backend}
      </p>
    </div>
  );
}
