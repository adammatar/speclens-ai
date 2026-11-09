import { useCallback, useEffect, useMemo, useState } from "react";
import { ChatPanel } from "../components/ChatPanel";
import { DocumentListPanel } from "../components/DocumentListPanel";
import {
  getDocument,
  getHealth,
  getMeta,
  listDocuments,
  uploadDocument,
  uploadDocumentVersion,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { runPostIngestPipeline, waitForJob } from "../lib/pipeline";
import type { ChatDocSelection, DocumentSummary, MetaInfo } from "../lib/types";

export function HomePage() {
  const { apiKey } = useAuth();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [meta, setMeta] = useState<MetaInfo | null>(null);
  const [health, setHealth] = useState("…");
  const [selected, setSelected] = useState<ChatDocSelection[]>([]);
  const [pipelineMessage, setPipelineMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!apiKey) return;
    const [list, m, h] = await Promise.all([
      listDocuments(apiKey),
      getMeta(),
      getHealth(),
    ]);
    setDocs(list);
    setMeta(m);
    setHealth(h.status);
  }, [apiKey]);

  useEffect(() => {
    refresh().catch((err) =>
      setError(err instanceof Error ? err.message : "Failed to load workspace"),
    );
  }, [refresh]);

  const availableDocs = useMemo(() => {
    // Build chat selections from latest succeeded versions (async filled below via effect)
    return selected.length
      ? selected
      : [];
  }, [selected]);

  const [catalog, setCatalog] = useState<ChatDocSelection[]>([]);

  useEffect(() => {
    if (!apiKey) return;
    let cancelled = false;
    (async () => {
      const ready = docs.filter((d) => d.latest_status === "succeeded");
      const rows: ChatDocSelection[] = [];
      for (const d of ready.slice(0, 40)) {
        try {
          const detail = await getDocument(apiKey, d.id);
          const latest = [...detail.versions].sort(
            (a, b) => b.version_number - a.version_number,
          )[0];
          if (!latest || latest.status !== "succeeded") continue;
          rows.push({
            documentId: d.id,
            title: d.title,
            versionId: latest.id,
            versionNumber: latest.version_number,
          });
        } catch {
          // skip
        }
      }
      if (!cancelled) setCatalog(rows);
    })();
    return () => {
      cancelled = true;
    };
  }, [apiKey, docs]);

  function toggleDoc(doc: ChatDocSelection) {
    setSelected((prev) => {
      const exists = prev.some((p) => p.documentId === doc.documentId);
      if (exists) return prev.filter((p) => p.documentId !== doc.documentId);
      return [...prev, doc];
    });
  }

  async function selectSummaryForChat(doc: DocumentSummary) {
    if (!apiKey || doc.latest_status !== "succeeded") return;
    const detail = await getDocument(apiKey, doc.id);
    const latest = [...detail.versions].sort(
      (a, b) => b.version_number - a.version_number,
    )[0];
    if (!latest) return;
    toggleDoc({
      documentId: doc.id,
      title: doc.title,
      versionId: latest.id,
      versionNumber: latest.version_number,
    });
  }

  async function processUpload(
    kind: "new" | "version",
    file: File,
    documentId?: string,
  ) {
    if (!apiKey) return;
    setBusy(true);
    setError(null);
    try {
      setPipelineMessage("Uploading…");
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

      setPipelineMessage("Reading and indexing…");
      await waitForJob(apiKey, accepted.job_id, (pct, status) => {
        setPipelineMessage(`Reading and indexing… ${status} (${pct}%)`);
      });

      await runPostIngestPipeline(apiKey, {
        versionId: accepted.document_version_id,
        previousVersionId,
        onEvent: (ev) => setPipelineMessage(ev.detail),
      });

      await refresh();
      const detail = await getDocument(apiKey, accepted.document_id);
      const latest = [...detail.versions].sort(
        (a, b) => b.version_number - a.version_number,
      )[0];
      if (latest) {
        setSelected((prev) => {
          const next = prev.filter((p) => p.documentId !== accepted.document_id);
          return [
            ...next,
            {
              documentId: accepted.document_id,
              title: detail.title,
              versionId: latest.id,
              versionNumber: latest.version_number,
            },
          ];
        });
      }
      setPipelineMessage(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setPipelineMessage(null);
    } finally {
      setBusy(false);
    }
  }

  const selectedIds = useMemo(
    () => new Set(selected.map((s) => s.documentId)),
    [selected],
  );

  return (
    <div className="home-split">
      <div className="stack" style={{ minHeight: 0 }}>
        {error ? <div className="error">{error}</div> : null}
        <DocumentListPanel
          docs={docs}
          meta={meta}
          health={health}
          selectedIds={selectedIds}
          onSelectForChat={(d) => {
            void selectSummaryForChat(d);
          }}
          onUpload={(file) => {
            void processUpload("new", file);
          }}
          onUploadVersion={(id, file) => {
            void processUpload("version", file, id);
          }}
          pipelineMessage={pipelineMessage}
          busy={busy}
        />
      </div>
      <ChatPanel
        selectedDocs={selected}
        onToggleDoc={toggleDoc}
        availableDocs={catalog.length ? catalog : availableDocs}
      />
    </div>
  );
}
