import { useState, type FormEvent } from "react";
import { decideChange, getComparison, startComparison } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { ComparisonJob } from "../lib/types";

export function ComparePage() {
  const { apiKey } = useAuth();
  const [baseId, setBaseId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [job, setJob] = useState<ComparisonJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function poll(jobId: string) {
    if (!apiKey) return;
    for (let i = 0; i < 40; i += 1) {
      const current = await getComparison(apiKey, jobId);
      setJob(current);
      if (current.status === "succeeded" || current.status === "failed") return;
      await new Promise((r) => window.setTimeout(r, 1000));
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!apiKey) return;
    setBusy(true);
    setError(null);
    try {
      const started = await startComparison(apiKey, baseId, targetId);
      await poll(started.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compare failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDecide(changeId: string, decision: "confirmed" | "rejected") {
    if (!apiKey || !job) return;
    await decideChange(apiKey, changeId, decision);
    const refreshed = await getComparison(apiKey, job.id);
    setJob(refreshed);
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Version compare</h1>
          <p>Align requirements between two document versions and confirm changes.</p>
        </div>
      </div>
      <form className="stack" onSubmit={onSubmit} style={{ maxWidth: 640 }}>
        <div className="field">
          <label htmlFor="base">Base document version id</label>
          <input id="base" value={baseId} onChange={(e) => setBaseId(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="target">Target document version id</label>
          <input
            id="target"
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            required
          />
        </div>
        {error ? <div className="error">{error}</div> : null}
        <button className="btn amber" type="submit" disabled={busy}>
          {busy ? "Comparing…" : "Start comparison"}
        </button>
      </form>
      {job ? (
        <div className="stack">
          <p className="muted">
            Job {job.status} · {job.change_count} changes · {job.progress_pct}%
          </p>
          <div className="list">
            {(job.changes || []).map((change) => (
              <div key={change.id} className="list-item" style={{ alignItems: "flex-start" }}>
                <div className="stack" style={{ gap: "0.35rem", flex: 1 }}>
                  <strong>{change.category}</strong>
                  <span className="muted">{change.old_statement || "—"}</span>
                  <span>{change.new_statement || "—"}</span>
                </div>
                <div className="stack">
                  <span className="badge">{change.decision}</span>
                  <button
                    className="btn secondary"
                    type="button"
                    onClick={() => onDecide(change.id, "confirmed")}
                  >
                    Confirm
                  </button>
                  <button
                    className="btn secondary"
                    type="button"
                    onClick={() => onDecide(change.id, "rejected")}
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
