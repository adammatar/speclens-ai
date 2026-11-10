import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  exportRequirements,
  getDocument,
  listDocuments,
  listRequirements,
  patchRequirement,
  startExtraction,
  getExtraction,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { useLocale } from "../lib/i18n";
import type { DocumentDetail, DocumentSummary, Requirement } from "../lib/types";

function sourceQuote(req: Requirement): string {
  const src = req.sources?.[0] as { source_quote?: string } | undefined;
  return src?.source_quote ?? "";
}

function sectionPath(req: Requirement): string {
  return (req as Requirement & { section_path?: string }).section_path ?? "—";
}

export function RequirementsPage() {
  const { apiKey } = useAuth();
  const { t } = useLocale();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [documentId, setDocumentId] = useState("");
  const [versionId, setVersionId] = useState("");
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendInfo, setBackendInfo] = useState<string | null>(null);

  useEffect(() => {
    if (!apiKey) return;
    listDocuments(apiKey)
      .then((rows) => {
        setDocs(rows);
        if (rows[0] && !documentId) setDocumentId(rows[0].id);
      })
      .catch((err: unknown) =>
        setError(err instanceof ApiError ? err.message : t("req.loadFailed")),
      );
  }, [apiKey, documentId, t]);

  useEffect(() => {
    if (!apiKey || !documentId) {
      setDetail(null);
      setVersionId("");
      return;
    }
    getDocument(apiKey, documentId)
      .then((doc) => {
        setDetail(doc);
        const ready = [...doc.versions]
          .filter((v) => v.status === "ready")
          .sort((a, b) => b.version_number - a.version_number);
        setVersionId(ready[0]?.id ?? doc.versions[0]?.id ?? "");
      })
      .catch((err: unknown) =>
        setError(err instanceof ApiError ? err.message : t("req.loadFailed")),
      );
  }, [apiKey, documentId, t]);

  const refresh = useCallback(async () => {
    if (!apiKey || !versionId) {
      setRequirements([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const rows = await listRequirements(apiKey, versionId);
      setRequirements(rows);
      const first = rows[0] as Requirement & {
        original_payload?: { model?: string; prompt_version?: string };
      };
      const payload = first?.original_payload;
      if (payload?.model || payload?.prompt_version) {
        setBackendInfo(
          [payload.model, payload.prompt_version].filter(Boolean).join(" · "),
        );
      } else {
        setBackendInfo(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("req.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [apiKey, versionId, t]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return requirements.filter((req) => {
      if (typeFilter !== "all" && req.requirement_type !== typeFilter) return false;
      if (statusFilter !== "all" && req.review_state !== statusFilter) return false;
      if (!q) return true;
      return (
        req.statement.toLowerCase().includes(q) ||
        sourceQuote(req).toLowerCase().includes(q) ||
        sectionPath(req).toLowerCase().includes(q)
      );
    });
  }, [requirements, query, typeFilter, statusFilter]);

  async function onExtract() {
    if (!apiKey || !versionId) return;
    setExtracting(true);
    setError(null);
    try {
      const started = await startExtraction(apiKey, versionId);
      for (let i = 0; i < 60; i++) {
        const job = await getExtraction(apiKey, started.job_id);
        if (job.status === "succeeded" || job.status === "failed") break;
        await new Promise((r) => setTimeout(r, 500));
      }
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("req.extractFailed"));
    } finally {
      setExtracting(false);
    }
  }

  async function onReview(id: string, review_state: "accepted" | "rejected" | "edited") {
    if (!apiKey) return;
    try {
      await patchRequirement(apiKey, id, { review_state });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("req.reviewFailed"));
    }
  }

  async function onExport(format: "json" | "csv") {
    if (!apiKey || !versionId) return;
    try {
      await exportRequirements(apiKey, versionId, format);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("req.exportFailed"));
    }
  }

  const versions = detail?.versions ?? [];

  return (
    <div className="main-pad stack">
      <div className="page-head">
        <div>
          <h1>{t("req.title")}</h1>
          <p>{t("req.subtitle")}</p>
        </div>
        <div className="row wrap">
          <button
            type="button"
            className="btn secondary sm"
            disabled={!versionId || extracting}
            onClick={() => void onExtract()}
          >
            {extracting ? t("req.extracting") : t("req.extract")}
          </button>
          <button
            type="button"
            className="btn secondary sm"
            disabled={!versionId || !requirements.length}
            onClick={() => void onExport("json")}
          >
            {t("req.exportJson")}
          </button>
          <button
            type="button"
            className="btn secondary sm"
            disabled={!versionId || !requirements.length}
            onClick={() => void onExport("csv")}
          >
            {t("req.exportCsv")}
          </button>
        </div>
      </div>

      <div className="doc-toolbar">
        <label className="sr-only" htmlFor="req-doc">
          {t("req.document")}
        </label>
        <select
          id="req-doc"
          value={documentId}
          onChange={(e) => setDocumentId(e.target.value)}
          aria-label={t("req.document")}
        >
          <option value="">{t("req.pickDocument")}</option>
          {docs.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.title}
            </option>
          ))}
        </select>
        <label className="sr-only" htmlFor="req-ver">
          {t("req.version")}
        </label>
        <select
          id="req-ver"
          value={versionId}
          onChange={(e) => setVersionId(e.target.value)}
          aria-label={t("req.version")}
          disabled={!versions.length}
        >
          {!versions.length ? <option value="">{t("req.noVersions")}</option> : null}
          {versions.map((v) => (
            <option key={v.id} value={v.id}>
              v{v.version_number} · {v.status}
            </option>
          ))}
        </select>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("req.search")}
          aria-label={t("req.search")}
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          aria-label={t("req.type")}
        >
          <option value="all">{t("req.allTypes")}</option>
          <option value="functional">functional</option>
          <option value="non_functional">non_functional</option>
          <option value="constraint">constraint</option>
          <option value="other">other</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label={t("req.status")}
        >
          <option value="all">{t("req.allStatus")}</option>
          <option value="proposed">proposed</option>
          <option value="accepted">accepted</option>
          <option value="edited">edited</option>
          <option value="rejected">rejected</option>
        </select>
      </div>

      {backendInfo ? (
        <p className="muted" style={{ fontSize: "0.85rem" }}>
          {t("req.backend")}: {backendInfo}
        </p>
      ) : null}
      {error ? <p className="error-text">{error}</p> : null}

      {loading ? <p className="muted">{t("req.loading")}</p> : null}
      {!loading && !versionId ? <p className="empty">{t("req.pickDocument")}</p> : null}
      {!loading && versionId && filtered.length === 0 ? (
        <p className="empty">{t("req.empty")}</p>
      ) : null}

      {filtered.length > 0 ? (
        <div
          className="table-wrap"
          role="region"
          aria-label={t("req.title")}
          data-testid="requirements-table"
        >
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">{t("req.statement")}</th>
                <th scope="col">{t("req.type")}</th>
                <th scope="col">{t("req.status")}</th>
                <th scope="col">{t("req.quote")}</th>
                <th scope="col">{t("req.provenance")}</th>
                <th scope="col">{t("req.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((req) => (
                <tr key={req.id} data-testid="requirement-row">
                  <td>{req.statement}</td>
                  <td>{req.requirement_type}</td>
                  <td>{req.review_state}</td>
                  <td className="muted" data-testid="requirement-quote">
                    {sourceQuote(req) || "—"}
                  </td>
                  <td className="muted" data-testid="requirement-provenance">
                    {sectionPath(req)}
                  </td>
                  <td>
                    <div className="row wrap">
                      <button
                        type="button"
                        className="btn secondary sm"
                        onClick={() => void onReview(req.id, "accepted")}
                      >
                        {t("req.accept")}
                      </button>
                      <button
                        type="button"
                        className="btn secondary sm"
                        onClick={() => void onReview(req.id, "rejected")}
                      >
                        {t("req.reject")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
