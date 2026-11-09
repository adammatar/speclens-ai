import { DEFAULT_WORKSPACE_ID } from "./types";
import type {
  AnswerTurn,
  Chunk,
  ComparisonJob,
  ConversationDetail,
  ConversationSummary,
  DocumentDetail,
  DocumentSummary,
  JobStatus,
  MetaInfo,
  Requirement,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeaders(apiKey: string): HeadersInit {
  return {
    Authorization: `Bearer ${apiKey}`,
  };
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    return JSON.stringify(body.detail ?? body);
  } catch {
    return response.statusText || "Request failed";
  }
}

async function request<T>(
  path: string,
  apiKey: string | null,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (apiKey) {
    headers.set("Authorization", `Bearer ${apiKey}`);
  }
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new ApiError(response.status, await parseError(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function getHealth(): Promise<{ status: string }> {
  return request("/api/v1/health", null);
}

export async function getMeta(): Promise<MetaInfo> {
  return request("/api/v1/meta", null);
}

export async function listDocuments(apiKey: string): Promise<DocumentSummary[]> {
  return request(
    `/api/v1/documents?workspace_id=${DEFAULT_WORKSPACE_ID}`,
    apiKey,
  );
}

export async function getDocument(apiKey: string, id: string): Promise<DocumentDetail> {
  return request(`/api/v1/documents/${id}`, apiKey);
}

export async function deleteDocument(apiKey: string, id: string): Promise<void> {
  await request(`/api/v1/documents/${id}`, apiKey, { method: "DELETE" });
}

export async function uploadDocument(
  apiKey: string,
  file: File,
  title?: string,
): Promise<{ document_id: string; document_version_id: string; job_id: string }> {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  return request("/api/v1/documents/upload", apiKey, { method: "POST", body: form });
}

export async function uploadDocumentVersion(
  apiKey: string,
  documentId: string,
  file: File,
): Promise<{ document_id: string; document_version_id: string; job_id: string }> {
  const form = new FormData();
  form.append("file", file);
  return request(`/api/v1/documents/${documentId}/versions`, apiKey, {
    method: "POST",
    body: form,
  });
}

export async function getJob(apiKey: string, jobId: string): Promise<JobStatus> {
  return request(`/api/v1/documents/jobs/${jobId}`, apiKey);
}

export async function listChunks(apiKey: string, versionId: string): Promise<Chunk[]> {
  return request(`/api/v1/documents/versions/${versionId}/chunks`, apiKey);
}

export async function startExtraction(
  apiKey: string,
  versionId: string,
): Promise<{ job_id: string; status: string }> {
  return request(`/api/v1/documents/versions/${versionId}/extractions`, apiKey, {
    method: "POST",
  });
}

export async function getExtraction(
  apiKey: string,
  jobId: string,
): Promise<{ status: string; progress_pct: number }> {
  return request(`/api/v1/extractions/${jobId}`, apiKey);
}

export async function listRequirements(
  apiKey: string,
  documentVersionId?: string,
): Promise<Requirement[]> {
  const qs = documentVersionId
    ? `?document_version_id=${documentVersionId}`
    : `?workspace_id=${DEFAULT_WORKSPACE_ID}`;
  return request(`/api/v1/requirements${qs}`, apiKey);
}

export async function listConversations(apiKey: string): Promise<ConversationSummary[]> {
  return request(
    `/api/v1/conversations?workspace_id=${DEFAULT_WORKSPACE_ID}`,
    apiKey,
  );
}

export async function getConversation(
  apiKey: string,
  conversationId: string,
): Promise<ConversationDetail> {
  return request(`/api/v1/conversations/${conversationId}`, apiKey);
}

export async function createConversation(
  apiKey: string,
  title: string,
): Promise<ConversationSummary> {
  return request(`/api/v1/conversations`, apiKey, {
    method: "POST",
    body: JSON.stringify({
      workspace_id: DEFAULT_WORKSPACE_ID,
      title,
    }),
  });
}

export async function postMessage(
  apiKey: string,
  conversationId: string,
  question: string,
  documentVersionIds?: string[],
): Promise<AnswerTurn> {
  return request(`/api/v1/conversations/${conversationId}/messages`, apiKey, {
    method: "POST",
    body: JSON.stringify({
      question,
      document_version_ids: documentVersionIds,
      stream: false,
    }),
  });
}

export async function startComparison(
  apiKey: string,
  baseVersionId: string,
  targetVersionId: string,
): Promise<{ job_id: string; status: string }> {
  return request(`/api/v1/comparisons`, apiKey, {
    method: "POST",
    body: JSON.stringify({
      base_document_version_id: baseVersionId,
      target_document_version_id: targetVersionId,
    }),
  });
}

export async function getComparison(apiKey: string, jobId: string): Promise<ComparisonJob> {
  return request(`/api/v1/comparisons/${jobId}`, apiKey);
}

export async function decideChange(
  apiKey: string,
  changeId: string,
  decision: "confirmed" | "rejected",
): Promise<RequirementChangeLite> {
  return request(`/api/v1/comparisons/changes/${changeId}`, apiKey, {
    method: "PATCH",
    body: JSON.stringify({ decision }),
  });
}

type RequirementChangeLite = {
  id: string;
  decision: string;
  is_eval_example: boolean;
};

export async function probeApiKey(apiKey: string): Promise<boolean> {
  try {
    await listDocuments(apiKey);
    return true;
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      return false;
    }
    throw error;
  }
}

export { authHeaders, API_BASE };
