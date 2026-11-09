/** Auto-generated from openapi.json - do not edit by hand. */
export const openApiTitle = "SpecLens AI API" as const;
export const openApiVersion = "0.1.0" as const;

export type ApiPath =
  | "/api/v1/health"
  | "/api/v1/ready";

export interface HealthResponse {
  status: "ok";
}

export interface ReadyResponse {
  status: "ok" | "unavailable";
  database: "up" | "down";
}

export const knownPaths: readonly ApiPath[] = [
  "/api/v1/health",
  "/api/v1/ready",
];
