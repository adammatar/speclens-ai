import { useEffect, useMemo, useState } from "react";
import {
  ApiError,
  decideChange,
  getComparison,
  getDocument,
  listDocuments,
  startComparison,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { useLocale } from "../lib/i18n";
import type {
  ComparisonJob,
  DocumentDetail,
  DocumentSummary,
  RequirementChange,
} from "../lib/types";

const CATEGORY_ORDER = [
  "added",
  "removed",
  "behavior_changed",
  "clarified",
  "priority_changed",
  "acceptance_criteria_changed",
  "potential_breaking_change",
  "uncertain",
];

export function ComparePage() {
  const { apiKey } = useAuth();
  const { t } = useLocale();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [documentId, setDocumentId] = useState("");
  const [baseId, setBaseId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [job, setJob] = useState<ComparisonJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!apiKey) return;
    listDocuments(apiKey)
      .then((rows) => {
        setDocs(rows);
        if (rows[0] && !documentId) setDocumentId(rows[0].id);
      })
      .catch((err: unknown) =>
        setError(err instanceof ApiError ? err.message : t("cmp.loadFailed")),
      );
  }, [apiKey, documentId, t]);

  useEffect(() => {
    if (!apiKey || !documentId) {
      setDetail(null);
      setBaseId("");
      setTargetId("");
      return;
    }
    getDocument(apiKey, documentId)
      .then((doc) => {
        setDetail(doc);
        const sorted = [...doc.versions].sort(
          (a, b) => a.version_number - b.version_number,
        );
        if (sorted.length >= 2) {
          setBaseId(sorted[sorted.length - 2].id);
          setTargetId(sorted[sorted.length - 1].id);
        } else if (sorted.length === 1) {
          setBaseId(sorted[0].id);
          setTargetId("");
        } else {
          setBaseId("");
          setTargetId("");
        }
      })
      .catch((err: unknown) =>
        setError(err instanceof ApiError ? err.message : t("cmp.loadFailed")),
      );
  }, [apiKey, documentId, t]);

  const grouped = useMemo(() => {
    const map = new Map<string, RequirementChange[]>();
    for (const cat of CATEGORY_ORDER) map.set(cat, []);
    for (const change of job?.changes ?? []) {
      const list = map.get(change.category) ?? [];
      list.push(change);
      map.set(change.category, list);
    }
    return CATEGORY_ORDER.map((cat) => ({
      category: cat,
      items: map.get(cat) ?? [],
    })).filter((g) => g.items.length > 0);
  }, [job]);

  async function onCompare() {
    if (!apiKey || !baseId || !targetId || baseId === targetId) return;
    setBusy(true);
    setError(null);
    setJob(null);
    try {
      const started = await startComparison(apiKey, baseId, targetId);
      let latest: ComparisonJob | null = null;
      for (let i = 0; i < 90; i++) {
        latest = await getComparison(apiKey, started.job_id);
        setJob(latest);
        if (latest.status === "succeeded" || latest.status === "failed") break;
        await new Promise((r) => setTimeout(r, 500));
      }
      if (latest?.status === "failed") {
        setError(t("cmp.failed"));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("cmp.failed"));
    } finally {
      setBusy(false);
    }
  }

  async function onDecide(changeId: string, decision: "confirmed" | "rejected") {
    if (!apiKey || !job) return;
    try {
      await decideChange(apiKey, changeId, decision);
      const latest = await getComparison(apiKey, job.id);
      setJob(latest);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("cmp.decideFailed"));
    }
  }

  const versions = detail?.versions ?? [];

  return (
    <div className="main-pad stack">
      <div className="page-head">
        <div>
          <h1>{t("cmp.title")}</h1>
          <p>{t("cmp.subtitle")}</p>
        </div>
        <button
          type="button"
          className="btn"
          data-testid="compare-start"
          disabled={busy || !baseId || !targetId || baseId === targetId}
          onClick={() => void onCompare()}
        >
          {busy ? t("cmp.running") : t("cmp.start")}
        </button>
      </div>

      <div className="doc-toolbar">
        <select
          value={documentId}
          onChange={(e) => setDocumentId(e.target.value)}
          aria-label={t("cmp.document")}
        >
          <option value="">{t("cmp.pickDocument")}</option>
          {docs.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.title}
            </option>
          ))}
        </select>
        <select
          value={baseId}
          onChange={(e) => setBaseId(e.target.value)}
          aria-label={t("cmp.base")}
          disabled={!versions.length}
        >
          <option value="">{t("cmp.base")}</option>
          {versions.map((v) => (
            <option key={v.id} value={v.id}>
              v{v.version_number} · {v.status}
            </option>
          ))}
        </select>
        <select
          value={targetId}
          onChange={(e) => setTargetId(e.target.value)}
          aria-label={t("cmp.target")}
          disabled={!versions.length}
        >
          <option value="">{t("cmp.target")}</option>
          {versions.map((v) => (
            <option key={v.id} value={v.id}>
              v{v.version_number} · {v.status}
            </option>
          ))}
        </select>
      </div>

      {error ? <p className="error-text">{error}</p> : null}

      {job ? (
        <p className="muted" style={{ fontSize: "0.9rem" }}>
          {t("cmp.progress", {
            status: job.status,
            pct: job.progress_pct,
            n: job.change_count,
          })}
        </p>
      ) : (
        <p className="empty">{t("cmp.empty")}</p>
      )}

      {grouped.map((group) => (
        <section key={group.category} className="stack" style={{ gap: "0.75rem" }}>
          <h2 style={{ fontSize: "1.05rem" }}>
            {t(`cmp.cat.${group.category}`)} ({group.items.length})
          </h2>
          <ul className="change-list" data-testid="compare-change-list">
            {group.items.map((change) => (
              <li key={change.id} className="change-item" data-testid="compare-change-item">
                <div className="stack" style={{ gap: "0.35rem" }}>
                  <strong>{change.category}</strong>
                  <p>
                    <span className="muted">{t("cmp.old")}: </span>
                    {change.old_statement ?? "—"}
                  </p>
                  <p>
                    <span className="muted">{t("cmp.new")}: </span>
                    {change.new_statement ?? "—"}
                  </p>
                  {(change.old_source_quote || change.new_source_quote) && (
                    <p className="muted" style={{ fontSize: "0.85rem" }}>
                      {t("cmp.evidence")}: {change.old_source_quote ?? "—"} →{" "}
                      {change.new_source_quote ?? "—"}
                    </p>
                  )}
                  <p className="muted" style={{ fontSize: "0.8rem" }}>
                    {t("cmp.decision")}: {change.decision}
                    {change.is_eval_example ? ` · ${t("cmp.evalExample")}` : ""}
                  </p>
                  <div className="row wrap">
                    <button
                      type="button"
                      className="btn secondary sm"
                      disabled={change.decision === "confirmed"}
                      onClick={() => void onDecide(change.id, "confirmed")}
                    >
                      {t("cmp.confirm")}
                    </button>
                    <button
                      type="button"
                      className="btn secondary sm"
                      disabled={change.decision === "rejected"}
                      onClick={() => void onDecide(change.id, "rejected")}
                    >
                      {t("cmp.reject")}
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
