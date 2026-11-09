#!/usr/bin/env node
/**
 * Phase 1 OpenAPI -> TypeScript contracts stub.
 *
 * Reads packages/contracts/openapi.json (exported from FastAPI) and writes a
 * minimal typed client surface. Later phases can swap this for openapi-typescript
 * or a similar generator without changing the package layout.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");
const openapiPath = join(root, "openapi.json");
const outPath = join(root, "src", "generated.ts");

const schema = JSON.parse(readFileSync(openapiPath, "utf8"));
const paths = schema.paths ?? {};
const pathKeys = Object.keys(paths).sort();

const lines = [];
lines.push("/** Auto-generated from openapi.json - do not edit by hand. */");
lines.push(`export const openApiTitle = ${JSON.stringify(schema.info?.title ?? "SpecLens AI API")} as const;`);
lines.push(`export const openApiVersion = ${JSON.stringify(schema.info?.version ?? "0.0.0")} as const;`);
lines.push("");
lines.push("export type ApiPath =");
if (pathKeys.length === 0) {
  lines.push("  | never;");
} else {
  pathKeys.forEach((p, i) => {
    const suffix = i === pathKeys.length - 1 ? ";" : "";
    lines.push(`  | ${JSON.stringify(p)}${suffix}`);
  });
}
lines.push("");
lines.push("export interface HealthResponse {");
lines.push('  status: "ok";');
lines.push("}");
lines.push("");
lines.push("export interface ReadyResponse {");
lines.push('  status: "ok" | "unavailable";');
lines.push('  database: "up" | "down";');
lines.push("}");
lines.push("");
lines.push("export const knownPaths: readonly ApiPath[] = [");
pathKeys.forEach((p) => {
  lines.push(`  ${JSON.stringify(p)},`);
});
lines.push("];");
lines.push("");

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, lines.join("\n"), "utf8");
console.log(`Wrote ${outPath} (${pathKeys.length} paths)`);
