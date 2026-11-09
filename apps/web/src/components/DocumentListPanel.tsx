import { useMemo, useRef, useState, type UIEvent } from "react";
import { Link } from "react-router-dom";
import { isDocReady, statusLabel } from "../lib/format";
import { useLocale } from "../lib/i18n";
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
  const { t } = useLocale();
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
          <h1>{t("home.title")}</h1>
          <p>{t("home.subtitle")}</p>
        </div>
        <button
          className="btn sm"
          type="button"
          disabled={busy}
          onClick={() => fileRef.current?.click()}
        >
          {t("home.upload")}
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
          <strong>{t("home.working")}</strong> · {pipelineMessage}
        </div>
      ) : null}

      <div className="stats-row">
        <div className="stat-chip">
          <strong>{docs.length}</strong>
          <span>{t("home.docs")}</span>
        </div>
        <div className="stat-chip">
          <strong>{docs.reduce((n, d) => n + d.version_count, 0)}</strong>
          <span>{t("home.versions")}</span>
        </div>
        <div className="stat-chip">
          <strong>{health}</strong>
          <span>{t("home.api")}</span>
        </div>
        <div className="stat-chip">
          <strong>{meta?.retention_days ?? "—"}</strong>
          <span>{t("home.retention")}</span>
        </div>
      </div>

      <div className="doc-toolbar">
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setVisible(5);
          }}
          placeholder={t("home.search")}
        />
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setVisible(5);
          }}
          style={{ maxWidth: 140 }}
        >
          <option value="all">{t("home.allStatus")}</option>
          <option value="ready">{t("home.statusReady")}</option>
          <option value="running">{t("home.statusReading")}</option>
          <option value="queued">{t("home.statusQueued")}</option>
          <option value="failed">{t("home.statusFailed")}</option>
        </select>
      </div>

      <div className="doc-scroll" onScroll={onScroll}>
        {shown.map((doc) => {
          const selected = selectedIds.has(doc.id);
          const badgeClass = isDocReady(doc.latest_status)
            ? "ready"
            : doc.latest_status === "failed"
              ? "failed"
              : "busy";
          return (
            <div key={doc.id} className="doc-row">
              <div className="doc-row-main">
                <strong>{doc.title}</strong>
                <span className="muted">
                  {doc.version_count} {t("home.versions").toLowerCase()} ·{" "}
                  <span className={`badge ${badgeClass}`}>{statusLabel(doc.latest_status)}</span>
                </span>
              </div>
              <div className="doc-row-actions">
                <button
                  type="button"
                  className={`btn sm ${selected ? "" : "secondary"}`}
                  onClick={() => onSelectForChat(doc)}
                  disabled={!isDocReady(doc.latest_status)}
                  title={
                    !isDocReady(doc.latest_status)
                      ? t("home.waitReady")
                      : selected
                        ? t("home.inChat")
                        : t("home.chat")
                  }
                >
                  {selected ? t("home.inChat") : t("home.chat")}
                </button>
                <button
                  type="button"
                  className="btn secondary sm"
                  disabled={busy}
                  onClick={() => versionRefs.current[doc.id]?.click()}
                >
                  {t("home.newVersion")}
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
        {!shown.length ? <div className="empty">{t("home.emptyDocs")}</div> : null}
        {shown.length < filtered.length ? (
          <div className="empty" style={{ padding: "0.5rem" }}>
            {t("home.scrollMore")}
          </div>
        ) : null}
      </div>

      <div className="panel-foot">
        <span className="muted" style={{ fontSize: "0.8rem" }}>
          Mode {meta?.deployment_mode ?? "…"} · {meta?.embedding_backend}/
          {meta?.generation_backend}/{meta?.extraction_backend}
        </span>
        <Link className="btn ghost sm" to="/documents">
          {t("home.seeAll")}
        </Link>
      </div>
    </section>
  );
}

export type { ChatDocSelection };
