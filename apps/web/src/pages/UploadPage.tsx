import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getJob, uploadDocument } from "../lib/api";
import { useAuth } from "../lib/auth";

export function UploadPage() {
  const { apiKey } = useAuth();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [docId, setDocId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!apiKey || !jobId) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const job = await getJob(apiKey, jobId);
        if (cancelled) return;
        setProgress(job.progress_pct);
        setStatus(job.status);
        if (job.status === "succeeded" && docId) {
          window.clearInterval(timer);
          navigate(`/documents/${docId}`);
        }
        if (job.status === "failed") {
          window.clearInterval(timer);
          setError(job.error_message || "Ingestion failed");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Job poll failed");
        }
      }
    }, 1000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [apiKey, jobId, docId, navigate]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!apiKey || !file) return;
    setBusy(true);
    setError(null);
    try {
      const result = await uploadDocument(apiKey, file, title || undefined);
      setJobId(result.job_id);
      setDocId(result.document_id);
      setStatus("queued");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Upload</h1>
          <p>Markdown, DOCX, or PDF — processed asynchronously by the worker.</p>
        </div>
        <Link className="btn secondary" to="/documents">
          Back to library
        </Link>
      </div>
      <form className="stack" onSubmit={onSubmit} style={{ maxWidth: 520 }}>
        <div className="field">
          <label htmlFor="title">Title (optional)</label>
          <input id="title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="file">File</label>
          <input
            id="file"
            type="file"
            accept=".md,.markdown,.docx,.pdf,text/markdown,application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        {error ? <div className="error">{error}</div> : null}
        {status ? (
          <p className="muted">
            Job {status} · {progress}%
          </p>
        ) : null}
        <button className="btn amber" type="submit" disabled={busy || !file}>
          {busy ? "Uploading…" : "Start ingest"}
        </button>
      </form>
    </div>
  );
}
