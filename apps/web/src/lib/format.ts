/** Client-facing answer cleanup — hide operator IDs and jargon. */

const UUID_RE =
  /\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b/g;

export function humanizeAnswer(content: string): string {
  let text = content.trim();
  text = text.replace(UUID_RE, "").replace(/\s{2,}/g, " ").trim();
  text = text.replace(/\s+([.,;:!?])/g, "$1");
  text = text.replace(/\[\s*\]/g, "");
  text = text.replace(/\(\s*\)/g, "");
  // Soften stub leftover phrasing if any
  text = text.replace(/^Based on the retrieved specification excerpts,\s*regarding\s*"[^"]+":\s*/i, "");
  text = text.replace(/\s*Citations refer only to retrieved chunk IDs\.?/gi, "");
  return text.trim();
}

export function isDocReady(status: string | null | undefined): boolean {
  const s = (status || "").toLowerCase();
  return s === "ready" || s === "succeeded" || s === "completed";
}

export function statusLabel(status: string | null | undefined): string {
  switch ((status || "").toLowerCase()) {
    case "queued":
    case "pending":
      return "Queued";
    case "running":
    case "processing":
      return "Reading";
    case "succeeded":
    case "ready":
    case "completed":
      return "Ready";
    case "failed":
      return "Failed";
    default:
      return status ? status.replace(/_/g, " ") : "Unknown";
  }
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}
