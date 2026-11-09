import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  deleteDocument,
  getDocument,
  listDocuments,
  uploadDocument,
  uploadDocumentVersion,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { statusLabel } from "../lib/format";
import { useLocale } from "../lib/i18n";
import { runPostIngestPipeline, waitForJob } from "../lib/pipeline";
import type { DocumentSummary } from "../lib/types";

export function DocumentsPage() {
  const { apiKey } = useAuth();
  const { t } = useLocale();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pipeline, setPipeline] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const versionRefs = useRef<Record<string, HTMLInputElement | null>>({});

  async function refresh() {
    if (!apiKey) return;
    setDocs(await listDocuments(apiKey));
  }

  useEffect(() => {
    refresh().catch((err) =>
      setError(err instanceof Error ? err.message : "Failed to load"),
    );
  }, [apiKey]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return docs.filter((d) => {
      if (q && !d.title.toLowerCase().includes(q)) return false;
      if (statusFilter !== "all" && (d.latest_status || "") !== statusFilter) return false;
      return true;
    });
  }, [docs, query, statusFilter]);

  async function handleUpload(kind: "new" | "version", file: File, documentId?: string) {
    if (!apiKey) return;
    setBusy(true);
    setError(null);
    try {
      setPipeline("Uploading…");
      let previousVersionId: string | null = null;
      if (kind === "version" && documentId) {
        const before = await getDocument(apiKey, documentId);
        const sorted = [...before.versions].sort(
          (a, b) => b.version_number - a.version_number,
        );
        previousVersionId = sorted[0]?.id ?? null;
      }
      const accepted =
        kind === "new"
          ? await uploadDocument(apiKey, file)
          : await uploadDocumentVersion(apiKey, documentId!, file);
      setPipeline("Reading and indexing…");
      await waitForJob(apiKey, accepted.job_id, (pct, status) =>
        setPipeline(`Reading… ${status} (${pct}%)`),
      );
      await runPostIngestPipeline(apiKey, {
        versionId: accepted.document_version_id,
        previousVersionId,
        onEvent: (ev) => setPipeline(ev.detail),
      });
      await refresh();
      setPipeline(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setPipeline(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="main-pad">
      <div className="page-head">
        <div>
          <h1>{t("docs.title")}</h1>
          <p>{t("docs.subtitle")}</p>
        </div>
        <button
          className="btn"
          type="button"
          disabled={busy}
          onClick={() => fileRef.current?.click()}
        >
          {t("docs.upload")}
        </button>
        <input
          ref={fileRef}
          type="file"
          hidden
          accept=".md,.markdown,.pdf,.docx,text/markdown,application/pdf"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleUpload("new", f);
            e.target.value = "";
          }}
        />
      </div>

      {error ? <div className="error" style={{ marginBottom: "0.75rem" }}>{error}</div> : null}
      {pipeline ? (
        <div className="pipeline" style={{ marginBottom: "0.75rem", borderRadius: 12 }}>
          {pipeline}
        </div>
      ) : null}

      <div className="doc-toolbar" style={{ padding: 0, marginBottom: "0.75rem" }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("docs.search")}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ maxWidth: 160 }}
        >
          <option value="all">{t("home.allStatus")}</option>
          <option value="succeeded">{t("home.statusReady")}</option>
          <option value="running">{t("home.statusReading")}</option>
          <option value="queued">{t("home.statusQueued")}</option>
          <option value="failed">{t("home.statusFailed")}</option>
        </select>
      </div>

      <div className="library-list">
        {filtered.map((doc) => {
          const badgeClass =
            doc.latest_status === "succeeded"
              ? "ready"
              : doc.latest_status === "failed"
                ? "failed"
                : "busy";
          return (
            <div key={doc.id} className="library-row">
              <div>
                <strong>
                  <Link to={`/documents/${doc.id}`}>{doc.title}</Link>
                </strong>
                <div className="muted" style={{ fontSize: "0.85rem", marginTop: 4 }}>
                  {doc.version_count} {t("home.versions").toLowerCase()} ·{" "}
                  <span className={`badge ${badgeClass}`}>{statusLabel(doc.latest_status)}</span>
                </div>
              </div>
              <div className="row">
                <button
                  type="button"
                  className="btn secondary sm"
                  disabled={busy}
                  onClick={() => versionRefs.current[doc.id]?.click()}
                >
                  {t("docs.newVersion")}
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
                    if (f) void handleUpload("version", f, doc.id);
                    e.target.value = "";
                  }}
                />
                <button
                  type="button"
                  className="btn danger sm"
                  onClick={async () => {
                    if (!apiKey) return;
                    if (!window.confirm(t("docs.confirmDelete", { title: doc.title }))) return;
                    await deleteDocument(apiKey, doc.id);
                    await refresh();
                  }}
                >
                  {t("docs.delete")}
                </button>
              </div>
            </div>
          );
        })}
        {!filtered.length ? <div className="empty">{t("docs.empty")}</div> : null}
      </div>
    </div>
  );
}
