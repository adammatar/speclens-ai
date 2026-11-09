import {
  getComparison,
  getExtraction,
  getJob,
  startComparison,
  startExtraction,
} from "./api";

export type PipelineStage =
  | "uploading"
  | "reading"
  | "indexing"
  | "extracting"
  | "comparing"
  | "ready"
  | "failed";

export type PipelineEvent = {
  stage: PipelineStage;
  detail: string;
  progress_pct?: number;
};

async function sleep(ms: number): Promise<void> {
  await new Promise((r) => window.setTimeout(r, ms));
}

export async function waitForJob(
  apiKey: string,
  jobId: string,
  onProgress?: (pct: number, status: string) => void,
): Promise<void> {
  for (let i = 0; i < 90; i += 1) {
    const job = await getJob(apiKey, jobId);
    onProgress?.(job.progress_pct, job.status);
    if (job.status === "succeeded") return;
    if (job.status === "failed") {
      throw new Error(job.error_message || "Processing failed");
    }
    await sleep(1000);
  }
  throw new Error("Timed out waiting for document processing");
}

export async function waitForExtraction(
  apiKey: string,
  jobId: string,
  onProgress?: (pct: number) => void,
): Promise<void> {
  for (let i = 0; i < 90; i += 1) {
    const job = await getExtraction(apiKey, jobId);
    onProgress?.(job.progress_pct);
    if (job.status === "succeeded") return;
    if (job.status === "failed") {
      throw new Error("Requirement extraction failed");
    }
    await sleep(1000);
  }
  throw new Error("Timed out waiting for extraction");
}

export async function waitForComparison(
  apiKey: string,
  jobId: string,
): Promise<void> {
  for (let i = 0; i < 90; i += 1) {
    const job = await getComparison(apiKey, jobId);
    if (job.status === "succeeded") return;
    if (job.status === "failed") {
      throw new Error("Version compare failed");
    }
    await sleep(1000);
  }
  throw new Error("Timed out waiting for compare");
}

/** After ingest succeeds: extract; if prior version exists, compare latest vs previous. */
export async function runPostIngestPipeline(
  apiKey: string,
  opts: {
    versionId: string;
    previousVersionId?: string | null;
    onEvent?: (event: PipelineEvent) => void;
  },
): Promise<void> {
  const { versionId, previousVersionId, onEvent } = opts;
  onEvent?.({ stage: "extracting", detail: "Finding structured requirements…" });
  try {
    const ext = await startExtraction(apiKey, versionId);
    await waitForExtraction(apiKey, ext.job_id, (pct) =>
      onEvent?.({ stage: "extracting", detail: "Extracting requirements…", progress_pct: pct }),
    );
  } catch {
    // Extraction is best-effort for the client UX; chat still works on chunks.
    onEvent?.({ stage: "extracting", detail: "Extraction skipped or failed — chat still available." });
  }

  if (previousVersionId) {
    onEvent?.({ stage: "comparing", detail: "Comparing with previous version…" });
    try {
      const cmp = await startComparison(apiKey, previousVersionId, versionId);
      await waitForComparison(apiKey, cmp.job_id);
    } catch {
      onEvent?.({ stage: "comparing", detail: "Compare skipped — you can still chat." });
    }
  }

  onEvent?.({ stage: "ready", detail: "Ready to chat" });
}
