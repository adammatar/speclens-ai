# SpecLens AI - Progress

## Phase 0-7

**Status:** Complete (approved) - PRs #1-#7

---

## Phase 8 - Security, authentication and privacy

**Status:** Complete and re-verified (awaiting review / merge; stop before Phase 9)

**Date:** 2026-11-09

**Branch:** `cursor/phase8-security-auth-018c`

**PR:** https://github.com/adammatar/speclens-ai/pull/8

### Architecture and implementation decisions

1. **Identity model:** Alembic revision `20261108_0007` adds `users`, `workspace_memberships` (roles `owner` / `editor` / `viewer`), `api_keys` (SHA-256 `key_hash` only), and append-only `audit_events`. Migration seeds default-workspace owner `local-admin@speclens.local` plus local/CI bootstrap key `speclens-local-dev-key`.
2. **Auth dependency:** `app.security.auth.require_api_key` accepts `Authorization: Bearer` or `X-API-Key`. Fail-closed when `AUTH_REQUIRED=true` (default). `/api/v1/health` and `/api/v1/ready` stay public. Unit tests may set `AUTH_REQUIRED=false` for DB-less cases.
3. **Authorization:** `require_workspace_role` ranks roles and is applied on documents, search, conversations, requirements, and comparisons (viewer for reads; editor for mutations). Cross-workspace IDs return 403.
4. **Hardening:** In-process rate limits on upload / QA / extract / compare (`RATE_LIMIT_PER_MINUTE`, default 120). Existing MIME/size allow-list retained. `RETENTION_DAYS` setting documents retention horizon (sweep job deferred).
5. **Privacy:** `app.security.redaction` strips Bearer tokens, API-key fields, and document body fields from structured logs / audit detail. Sensitive route actions write `audit_events` without raw bodies.
6. **Contracts / CI:** OpenAPI advertises `BearerAuth` + `ApiKeyHeader` on protected paths. Compose smoke asserts 401 without a key and uses the bootstrap Bearer for the full ingest → search → QA → extract → compare path.

### Acceptance criteria (technical-plan exit criteria)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Cross-workspace access denied | Yes | `test_cross_workspace_access_denied` (doc GET + search → 403); viewer upload → 403 |
| Deleted docs absent from storage/chunks/embeddings | Yes | `test_bootstrap_key_upload_delete_clears_artifacts` (storage key gone; no chunks/embeddings rows) |
| API keys never reach the frontend | Yes | `rg` over `apps/` + `packages/contracts/src` finds no key material; secrets stay in `.env.example` / server docs |
| Logs hold IDs/metrics, not confidential content | Yes | `test_redaction_strips_secrets_and_bodies` + JSON formatter wiring in `app.core.logging` |
| Security checklist documented | Yes | `docs/security.md` checklist + backup/restore + secret management |

### Changed files (vs Phase 7)

```text
.env.example
.github/workflows/ci.yml
README.md
docs/progress.md
docs/security.md
packages/contracts/openapi.json
pyproject.toml
services/api/app/api/routes/comparisons.py
services/api/app/api/routes/conversations.py
services/api/app/api/routes/documents.py
services/api/app/api/routes/requirements.py
services/api/app/api/routes/search.py
services/api/app/core/config.py
services/api/app/core/logging.py
services/api/app/db/models.py
services/api/app/main.py
services/api/app/security/__init__.py
services/api/app/security/audit.py
services/api/app/security/auth.py
services/api/app/security/rate_limit.py
services/api/app/security/redaction.py
services/api/app/security/workspace.py
services/api/migrations/versions/20261108_0007_security_auth.py
services/api/tests/conftest.py
services/api/tests/test_security_auth.py
```

### Commands / results (re-verification 2026-11-09)

```text
ruff check services/api workers evals scripts     -> pass
ruff format --check ...                           -> pass (112 files)
python3 -m mypy                                   -> Success (71 source files)
python3 -m pytest                                 -> 48 passed, 1 warning (Starlette TestClient deprecation)
python -m evals.harness                           -> all gates passed
python -m evals.harness --enforce                 -> all gates passed
Local compose: health 200; upload without key 401; upload with Bearer accepted
GitHub CI (PR #8): Lint/typecheck/pytest SUCCESS; Evaluation harness SUCCESS;
                   Compose smoke was still running at re-verify time
```

**Failures:** none locally. CI compose smoke was in progress at documentation time (lint + eval already green).

### Explicit stop

Phase 9 (production UX and deployment) is **not started**. Awaiting explicit approval.

### Remaining risks

1. Bootstrap API key is a documented local/CI secret - rotate/disable before any shared or hosted deploy.
2. Rate limiter is in-process per API replica (not Redis-backed); multi-replica hosted deploys need a shared limiter.
3. `RETENTION_DAYS` is configuration + docs only; no scheduled purge job yet (complete delete API covers explicit wipe).
4. Auth is API-key based (no browser session/OIDC yet) - Phase 9 frontend must avoid embedding secrets in the bundle.

---

## Phase 9 plan (proposed) - Production UX and deployment

**Do not execute until explicitly approved.**

### Goal

Deliver a usable Nuxt frontend against the authenticated Phase 8 API, plus a reproducible production-style deployment path (images, managed data plane, HTTPS, monitoring, backups) and a resettable public demo on non-confidential documents.

### Scope (in)

1. **Frontend (`apps/web` Nuxt)**
   - Sign-in that stores the API key/session client-side only (never bake OpenAI or bootstrap secrets into the bundle).
   - Workspace dashboard, document library, upload + job progress, document viewer.
   - Cited AI chat, requirements workspace, version comparison, evaluation dashboard, settings/retention controls.
   - Consume `packages/contracts` OpenAPI types; send `Authorization: Bearer` on all protected calls.
2. **Deployment**
   - Production Docker images for API + worker (+ web).
   - Managed PostgreSQL with pgvector, Redis, object storage.
   - HTTPS termination, health/ready probes, basic monitoring and error tracking.
3. **Ops**
   - Migration + rollback runbook.
   - Backup and restore drill (DB dump + object store) documented and exercised once.
   - Public demo workspace with non-confidential corpus and a safe reset script.

### Non-goals

- Enterprise SSO/SCIM / customer-managed KMS
- Electron desktop packaging
- Phase 10 portfolio packaging (screenshots, demo video, write-up)

### Exit criteria to verify before stop

| Criterion | How we will prove it |
| --- | --- |
| Fresh production deployment works from documented instructions | Follow deploy docs on a clean environment / Compose prod profile |
| Demo can be reset safely | Scripted wipe of demo workspace + re-seed; smoke after reset |
| Health checks and monitoring work | Probes green; at least one metrics/error sink wired |
| Backup restoration tested | Restore dump + storage into a scratch stack; ready + search smoke |
| No confidential sample files published | Demo corpus review; gitignore / publish checklist |

### Implementation sketch

1. Branch `cursor/phase9-production-ux-018c` from Phase 8.
2. Scaffold/expand Nuxt app; thin vertical slices per page wired to real API with auth header.
3. Prod Compose/image targets, deploy + backup/restore docs, demo reset script.
4. Tests (frontend unit/e2e smoke where practical) + CI; update `docs/progress.md`; open PR; **stop for Phase 10 approval**.

### Risks for Phase 9

- Frontend scope creep across many pages - prefer thin slices over polish-first.
- Accidental secret leakage if demo/prod envs reuse the local bootstrap key.
- Backup consistency between Postgres and object storage during demo reset.
- Auth UX gap (raw API key in browser) until optional OIDC lands later.
