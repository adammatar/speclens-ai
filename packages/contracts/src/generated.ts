/** Auto-generated from openapi.json - do not edit by hand. */
export const openApiTitle = "SpecLens AI API" as const;
export const openApiVersion = "0.1.0" as const;

export type ApiPath =
  | "/api/v1/documents/jobs/{job_id}"
  | "/api/v1/documents/upload"
  | "/api/v1/documents/versions/{document_version_id}/chunks"
  | "/api/v1/documents/versions/{document_version_id}/reprocess"
  | "/api/v1/documents/{document_id}"
  | "/api/v1/health"
  | "/api/v1/ready"
  | "/api/v1/search"
  | "/api/v1/search/debug";

export interface HealthResponse {
  status: "ok";
}

export interface ReadyResponse {
  status: "ok" | "unavailable";
  database: "up" | "down";
}

export const knownPaths: readonly ApiPath[] = [
  "/api/v1/documents/jobs/{job_id}",
  "/api/v1/documents/upload",
  "/api/v1/documents/versions/{document_version_id}/chunks",
  "/api/v1/documents/versions/{document_version_id}/reprocess",
  "/api/v1/documents/{document_id}",
  "/api/v1/health",
  "/api/v1/ready",
  "/api/v1/search",
  "/api/v1/search/debug",
];
