import { useMemo, useRef, useState, type UIEvent } from "react";
import { Link } from "react-router-dom";
import { statusLabel } from "../lib/format";
import type { ChatDocSelection, DocumentSummary, MetaInfo } from "../lib/types";

type Props = {
  docs: DocumentSummary[];
  meta: MetaInfo | null;
  health: string;
  selectedIds: Set<string>;
  onSelectForChat: (doc: DocumentSummary) => void;
  onUpload: (file: File) => void;
  onUploadVersion: (documentId: string, file: File) => void;
  pipelineMessage: string | null;
  busy: boolean;
};

export function DocumentListPanel({
  docs,
  meta,
  health,
  selectedIds,
  onSelectForChat,
  onUpload,
  onUploadVersion,
  pipelineMessage,
  busy,
}: Props) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [visible, setVisible] = useState(5);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const versionRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return docs.filter((d) => {
      if (q && !d.title.toLowerCase().includes(q)) return false;
      if (statusFilter !== "all" && (d.latest_status || "") !== statusFilter) return false;
      return true;
    });
  }, [docs, query, statusFilter]);

  const shown = filtered.slice(0, visible);

  function onScroll(e: UIEvent<HTMLDivElement>) {
    const el = e.currentTarget;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 8) {
      setVisible((v) => Math.min(filtered.length, v + 5));
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h1>Workspace</h1>
          <p>Your files and live stats — chat stays on the right.</p>
        </div>
        <button className="btn sm" type="button" disabled={busy} onClick={() => fileRef.current?.click()}>
          Upload
        </button>
        <input
          ref={fileRef}
          type="file"
          hidden
          accept=".md,.markdown,.pdf,.docx,text/markdown,application/pdf"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onUpload(f);
            e.target.value = "";
          }}
        />
      </div>

      {pipelineMessage ? (
        <div className="pipeline">
          <strong>Working</strong> · {pipelineMessage}
        </div>
      ) : null}

      <div className="stats-row">
        <div className="stat-chip">
          <strong>{docs.length}</strong>
          <span>Documents</span>
        </div>
        <div className="stat-chip">
          <strong>{docs.reduce((n, d) => n + d.version_count, 0)}</strong>
          <span>Versions</span>
        </div>
        <div className="stat-chip">
          <strong>{health}</strong>
          <span>API</span>
        </div>
        <div className="stat-chip">
          <strong>{meta?.retention_days ?? "—"}</strong>
          <span>Retention days</span>
        </div>
      </div>

      <div className="doc-toolbar">
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setVisible(5);
          }}
          placeholder="Search documents"
        />
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setVisible(5);
          }}
          style={{ maxWidth: 140 }}
        >
          <option value="all">All status</option>
          <option value="succeeded">Ready</option>
          <option value="running">Reading</option>
          <option value="queued">Queued</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className="doc-scroll" onScroll={onScroll}>
        {shown.map((doc) => {
          const selected = selectedIds.has(doc.id);
          const badgeClass =
            doc.latest_status === "succeeded"
              ? "ready"
              : doc.latest_status === "failed"
                ? "failed"
                : "busy";
          return (
            <div key={doc.id} className="doc-row">
              <div className="doc-row-main">
                <strong>{doc.title}</strong>
                <span className="muted">
                  {doc.version_count} version{doc.version_count === 1 ? "" : "s"} ·{" "}
                  <span className={`badge ${badgeClass}`}>{statusLabel(doc.latest_status)}</span>
                </span>
              </div>
              <div className="doc-row-actions">
                <button
                  type="button"
                  className={`btn sm ${selected ? "" : "secondary"}`}
                  onClick={() => onSelectForChat(doc)}
                  disabled={doc.latest_status !== "succeeded"}
                  title={
                    doc.latest_status !== "succeeded"
                      ? "Wait until the document is Ready"
                      : selected
                        ? "Selected for chat"
                        : "Use in chat"
                  }
                >
                  {selected ? "In chat" : "Chat"}
                </button>
                <button
                  type="button"
                  className="btn secondary sm"
                  disabled={busy}
                  onClick={() => versionRefs.current[doc.id]?.click()}
                >
                  New version
                </button>
                <input
                  ref={(el) => {
                    versionRefs.current[doc.id] = el;
                  }}
                  type="file"
                  hidden
                  accept=".md,.markdown,.pdf,.docx,text/markdown,application/pdf"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) onUploadVersion(doc.id, f);
                    e.target.value = "";
                  }}
                />
              </div>
            </div>
          );
        })}
        {!shown.length ? <div className="empty">No documents yet. Upload a file to begin.</div> : null}
        {shown.length < filtered.length ? (
          <div className="empty" style={{ padding: "0.5rem" }}>
            Scroll for more…
          </div>
        ) : null}
      </div>

      <div className="panel-foot">
        <span className="muted" style={{ fontSize: "0.8rem" }}>
          Mode {meta?.deployment_mode ?? "…"} · {meta?.embedding_backend}/
          {meta?.generation_backend}/{meta?.extraction_backend}
        </span>
        <Link className="btn ghost sm" to="/documents">
          See all documents
        </Link>
      </div>
    </section>
  );
}

export type { ChatDocSelection };
