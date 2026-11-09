import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  deleteDocument,
  getDocument,
  listChunks,
  uploadDocumentVersion,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatBytes, statusLabel } from "../lib/format";
import { useLocale } from "../lib/i18n";
import { runPostIngestPipeline, waitForJob } from "../lib/pipeline";
import type { Chunk, DocumentDetail } from "../lib/types";

export function DocumentDetailPage() {
  const { id = "" } = useParams();
  const { apiKey } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pipeline, setPipeline] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const versions = useMemo(() => {
    if (!doc) return [];
    return [...doc.versions].sort((a, b) => b.version_number - a.version_number);
  }, [doc]);

  const latest = versions[0] ?? null;
  const previous = versions[1] ?? null;

  async function refresh() {
    if (!apiKey || !id) return;
    const detail = await getDocument(apiKey, id);
    setDoc(detail);
    const sorted = [...detail.versions].sort((a, b) => b.version_number - a.version_number);
    if (sorted[0]) {
      setChunks(await listChunks(apiKey, sorted[0].id));
    }
  }

  useEffect(() => {
    refresh().catch((err) =>
      setError(err instanceof Error ? err.message : "Load failed"),
    );
  }, [apiKey, id]);

  async function onNewVersion(file: File) {
    if (!apiKey || !id) return;
    setBusy(true);
    setError(null);
    try {
      setPipeline("Uploading new version…");
      const accepted = await uploadDocumentVersion(apiKey, id, file);
      setPipeline("Reading and indexing…");
      await waitForJob(apiKey, accepted.job_id, (pct, status) =>
        setPipeline(`Reading… ${status} (${pct}%)`),
      );
      await runPostIngestPipeline(apiKey, {
        versionId: accepted.document_version_id,
        previousVersionId: latest?.id ?? null,
        onEvent: (ev) => setPipeline(ev.detail),
      });
      await refresh();
      setPipeline(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Version upload failed");
      setPipeline(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="main-pad stack">
      <div className="page-head">
        <div>
          <h1>{doc?.title ?? "Document"}</h1>
          <p>{t("detail.lede")}</p>
        </div>
        <div className="row">
          <Link className="btn secondary" to="/documents">
            {t("detail.library")}
          </Link>
          <Link className="btn secondary" to="/">
            {t("detail.homeChat")}
          </Link>
          <button
            className="btn"
            type="button"
            disabled={busy}
            onClick={() => fileRef.current?.click()}
          >
            {t("detail.uploadVersion")}
          </button>
          <input
            ref={fileRef}
            type="file"
            hidden
            accept=".md,.markdown,.pdf,.docx,text/markdown,application/pdf"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void onNewVersion(f);
              e.target.value = "";
            }}
          />
          <button
            className="btn danger"
            type="button"
            onClick={async () => {
              if (!apiKey || !id) return;
              if (!window.confirm(t("detail.confirmDelete"))) return;
              await deleteDocument(apiKey, id);
              navigate("/documents");
            }}
          >
            {t("detail.delete")}
          </button>
        </div>
      </div>

      {error ? <div className="error">{error}</div> : null}
      {pipeline ? <div className="pipeline" style={{ borderRadius: 12 }}>{pipeline}</div> : null}

      <div className="version-list">
        {versions.slice(0, 2).map((v, idx) => (
          <div key={v.id} className="version-card">
            <div>
              <strong>
                {idx === 0 ? t("detail.latest") : t("detail.previous")} · v{v.version_number}
              </strong>
              <div className="muted" style={{ fontSize: "0.85rem", marginTop: 4 }}>
                {v.filename} · {formatBytes(v.byte_size)} ·{" "}
                <span className={`badge ${v.status === "succeeded" ? "ready" : "busy"}`}>
                  {statusLabel(v.status)}
                </span>
                {idx === 0 && previous ? t("detail.kept") : null}
              </div>
            </div>
          </div>
        ))}
        {!versions.length ? <div className="empty">{t("detail.noVersions")}</div> : null}
      </div>

      <div className="stack" style={{ marginTop: "0.5rem" }}>
        <h2 style={{ fontSize: "1.05rem" }}>{t("detail.preview")}</h2>
        {chunks.slice(0, 8).map((chunk) => (
          <article key={chunk.id} className="version-card" style={{ display: "block" }}>
            <h3 style={{ fontSize: "0.92rem", marginBottom: 6 }}>
              {chunk.heading_path || `Section ${chunk.chunk_index + 1}`}
            </h3>
            <p className="muted" style={{ whiteSpace: "pre-wrap" }}>
              {chunk.text.slice(0, 500)}
              {chunk.text.length > 500 ? "…" : ""}
            </p>
          </article>
        ))}
        {!chunks.length ? <p className="muted">{t("detail.noPreview")}</p> : null}
      </div>
    </div>
  );
}
