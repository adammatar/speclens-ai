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

Logs may contain IDs, timings, token counts, model names - **not** raw document bodies, prompts with full context dumps, or API keys. Structured logging runs through `app.security.redaction`.

## AI-specific rules

1. Documents are data, not executable instructions (prompt-injection defenses from Phase 4/7/8).
2. No answer claim without retrieved evidence; never invent citations.
3. API keys and OpenAI credentials stay server-side only.
4. Complete deletion must remove object bytes, chunks, embeddings, and derived requirements.
5. Cross-workspace access must fail closed; every query filters by workspace.

## Authentication and authorization (Phase 8)

- **API keys:** `Authorization: Bearer <key>` or `X-API-Key: <key>`. Keys are stored as SHA-256 hashes (`api_keys.key_hash`); plaintext is never persisted.
- **Roles:** `owner` > `editor` > `viewer` via `workspace_memberships`.
- **Public routes:** `/api/v1/health` and `/api/v1/ready` only.
- **Local/CI bootstrap:** migration seeds `local-admin@speclens.local` as owner of the default workspace with key `speclens-local-dev-key` (documented in `.env.example` only - not for production).
- **Rate limits:** in-process per-key buckets on upload / QA / extract / compare (`RATE_LIMIT_PER_MINUTE`, default 120).
- **Audit:** `audit_events` for upload, delete, export, requirement accept, and change confirm (no document bodies in `detail`).

## Local mode vs hosted mode

| Concern | Local mode | Hosted mode |
| --- | --- | --- |
| Document location | Local disk / local object store | Managed object storage |
| Auth | Bootstrap API key + hashed keys | Real auth + RBAC (OIDC later) |
| Outbound LLM | Optional / user-configured key | Platform-managed |
| Network exposure | Bind localhost by default | HTTPS public API |
| Retention | `RETENTION_DAYS` + user wipe | Configurable retention + audit |

## Secret management

1. Copy `.env.example` → `.env` locally; never commit `.env`.
2. Compose loads `.env.example` for stub stacks; replace passwords/keys before any shared environment.
3. OpenAI keys stay in server env only - never ship in `apps/web` or contracts packages.
4. Rotate the bootstrap API key before production by inserting a new hashed key and disabling the seed key.

## Upload hardening

- Max size: `MAX_UPLOAD_BYTES` (default 50 MiB).
- Allow-list: `.md` / `.markdown` / `.docx` / `.pdf` with matching content types (`app.ingestion.validate`).
- Deduped by SHA-256 within a workspace.

## Retention and deletion

- `RETENTION_DAYS` (default 365) is the configured retention horizon for hosted policy docs and future sweep jobs.
- `DELETE /api/v1/documents/{id}` removes DB rows (cascading chunks/embeddings/jobs) and object-store bytes.
- Derived requirements/comparisons cascade with document versions.

## Backup and restore (local / Compose)

1. **Logical backup:** `docker compose -f infra/compose.yaml exec -T postgres pg_dump -U speclens speclens > backup.sql`
2. **Object store:** copy `data/storage/` alongside the dump.
3. **Restore:** recreate volumes (`make down`), `make up`, then `psql` restore and restore `data/storage/`.
4. Verify with `/api/v1/ready` and a authenticated document list/search smoke.
5. Hosted deployments should use managed Postgres PITR + object-store versioning (Phase 9).

## Security checklist (Phase 8)

| Check | Status |
| --- | --- |
| Cross-workspace access denied | Tests in `test_security_auth.py` |
| Missing/invalid API key → 401 | Tests + CI smoke |
| Health/ready public | Tests + CI |
| Delete clears storage/chunks/embeddings | Auth delete test |
| API keys absent from frontend bundle | No key material under `apps/web` |
| Logs redact secrets/bodies | Redaction unit tests + JSON formatter |
| Upload MIME/size allow-list | `validate_upload` |
| Audit events for sensitive actions | `audit_events` + route hooks |
| Prompt-injection suite | `evals/datasets/injection_v1.jsonl` |

## Threats to track

- XSS via rendered document HTML (`v-html` pattern in current viewer)
- Path traversal on file/object keys (current Electron protocol already guards static root)
- Tenant confusion / IDOR on document and chat IDs
- Prompt injection via malicious specs
- Secret leakage into frontend bundles or CI logs
- Residual embeddings after "delete"
