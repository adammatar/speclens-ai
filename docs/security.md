# SpecLens AI - Security and Privacy Boundaries

## Trust model

| Zone | Trust | Notes |
| --- | --- | --- |
| Browser / Nuxt UI | Untrusted | No secrets; sessions/tokens only |
| Electron shell (future optional) | Semi-trusted local | Same as today: contextIsolation, no nodeIntegration |
| FastAPI API | Trusted compute | Enforces workspace ACL |
| Workers | Trusted compute | Same secrets plane as API |
| Postgres / Redis / object store | Trusted data plane | Encrypted at rest in hosted deployments |
| OpenAI API | External processor | Document excerpts leave the trust boundary when AI features are used |
| Uploaded documents | **Untrusted data** | Never treat document text as instructions |

## Boundaries carried forward from Local Docs Viewer

Existing app strengths to keep as requirements for **local mode**:

- Source files are not committed to git (gitignore `*.docx` etc.)
- No analytics/telemetry by default
- Parsed caches are user-local and deletable
- Read-only viewing of source Word files

SpecLens hosted mode necessarily introduces upload and cloud processing; that must be explicit in UX copy (contrast with "No upload" welcome screen today).

## Data classification

- **Confidential:** uploaded technical specs, extracted requirements, chat transcripts with quotes
- **Internal:** workspace membership, job status, eval datasets derived from redacted docs
- **Public:** product marketing, synthetic demo documents only

Logs may contain IDs, timings, token counts, model names - **not** raw document bodies, prompts with full context dumps, or API keys.

## AI-specific rules

1. Documents are data, not executable instructions (prompt-injection defenses from Phase 4/7/8).
2. No answer claim without retrieved evidence; never invent citations.
3. API keys and OpenAI credentials stay server-side only.
4. Complete deletion must remove object bytes, chunks, embeddings, and derived requirements.
5. Cross-workspace access must fail closed; every query filters by workspace.

## Local mode vs hosted mode

| Concern | Local mode | Hosted mode |
| --- | --- | --- |
| Document location | Local disk / local object store | Managed object storage |
| Auth | Single-user or local accounts | Real auth + RBAC |
| Outbound LLM | Optional / user-configured key | Platform-managed |
| Network exposure | Bind localhost by default | HTTPS public API |
| Retention | User-controlled wipe | Configurable retention + audit |

## Threats to track

- XSS via rendered document HTML (`v-html` pattern in current viewer)
- Path traversal on file/object keys (current Electron protocol already guards static root)
- Tenant confusion / IDOR on document and chat IDs
- Prompt injection via malicious specs
- Secret leakage into frontend bundles or CI logs
- Residual embeddings after "delete"

## Phase 0 non-implementations

No auth code, rate limits, or hardening shipped yet. This document is the contract Phase 1+ must respect when scaffolding settings and Compose networking (no published Postgres/Redis ports in production profiles without auth).
