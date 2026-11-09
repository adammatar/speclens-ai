import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { deleteDocument, getDocument, listChunks, startExtraction } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Chunk, DocumentDetail } from "../lib/types";

export function DocumentDetailPage() {
  const { id = "" } = useParams();
  const { apiKey } = useAuth();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [extractStatus, setExtractStatus] = useState<string | null>(null);

  const latest = useMemo(() => {
    if (!doc?.versions.length) return null;
    return [...doc.versions].sort((a, b) => b.version_number - a.version_number)[0];
  }, [doc]);

  useEffect(() => {
    if (!apiKey || !id) return;
    getDocument(apiKey, id)
      .then(setDoc)
      .catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, [apiKey, id]);

  useEffect(() => {
    if (!apiKey || !latest) return;
    listChunks(apiKey, latest.id)
      .then(setChunks)
      .catch(() => setChunks([]));
  }, [apiKey, latest]);

  async function onExtract() {
    if (!apiKey || !latest) return;
    setExtractStatus("starting");
    try {
      const job = await startExtraction(apiKey, latest.id);
      setExtractStatus(`queued ${job.job_id}`);
      navigate(`/requirements?version=${latest.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extraction failed");
      setExtractStatus(null);
    }
  }

  async function onDelete() {
    if (!apiKey || !id) return;
    if (!window.confirm("Delete this document and all derived data?")) return;
    await deleteDocument(apiKey, id);
    navigate("/documents");
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>{doc?.title ?? "Document"}</h1>
          <p>Viewer for chunks and version metadata.</p>
        </div>
        <div className="row">
          <Link className="btn secondary" to="/documents">
            Library
          </Link>
          <button className="btn" type="button" onClick={onExtract} disabled={!latest}>
            Extract requirements
          </button>
          <button className="btn secondary" type="button" onClick={onDelete}>
            Delete
          </button>
        </div>
      </div>
      {error ? <div className="error">{error}</div> : null}
      {latest ? (
        <p className="muted">
          Version {latest.version_number} · {latest.filename} · {latest.status} ·{" "}
          {latest.chunk_count} chunks
          {extractStatus ? ` · extract ${extractStatus}` : ""}
        </p>
      ) : null}
      <div className="stack">
        {chunks.map((chunk) => (
          <article key={chunk.id} className="chunk">
            <h3>
              {chunk.heading_path || `Chunk ${chunk.chunk_index}`}
              {chunk.page_number != null ? ` · p.${chunk.page_number}` : ""}
            </h3>
            <p className="prose">{chunk.text}</p>
          </article>
        ))}
        {!chunks.length ? <p className="muted">No chunks yet (ingest may still be running).</p> : null}
      </div>
    </div>
  );
}
