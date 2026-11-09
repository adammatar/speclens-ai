# SpecLens AI - Progress

## Phase 0-7

**Status:** Complete (approved) - PRs #1-#7

---

## Phase 8 - Security, authentication and privacy

**Status:** Complete (awaiting review / merge; stop before Phase 9)

**Date:** 2026-11-09

**Branch:** `cursor/phase8-security-auth-018c`

**PR:** (opened against Phase 7 branch)

### Architecture and implementation decisions

1. Migration `20261108_0007` adds `users`, `workspace_memberships`, `api_keys`, `audit_events` plus bootstrap owner + hashed local API key.
2. `require_api_key` accepts Bearer or `X-API-Key`; keys stored as SHA-256; `/health` and `/ready` remain public.
3. Workspace RBAC (`owner` / `editor` / `viewer`) enforced on documents, search, conversations, requirements, comparisons.
4. In-process rate limits on upload/QA/extract/compare; `AUTH_REQUIRED`, `RATE_LIMIT_PER_MINUTE`, `RETENTION_DAYS` settings.
5. Structured log redaction + audit events for upload/delete/export/accept/confirm (no document bodies).
6. OpenAPI security schemes (`BearerAuth`, `ApiKeyHeader`); CI compose smoke sends bootstrap Bearer token and asserts 401 without it.

### Acceptance criteria (technical-plan exit criteria)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Cross-workspace access denied | Yes | `test_cross_workspace_access_denied` |
| Deleted docs absent from storage/chunks/embeddings | Yes | `test_bootstrap_key_upload_delete_clears_artifacts` |
| API keys never reach the frontend | Yes | no key material under `apps/web`; contracts/docs only |
| Logs hold IDs/metrics, not confidential content | Yes | redaction unit tests + JSON formatter |
| Security checklist documented | Yes | `docs/security.md` |

### Changed files (highlights)

```text
.github/workflows/ci.yml
.env.example
README.md
docs/progress.md
docs/security.md
packages/contracts/openapi.json
packages/contracts/src/generated.ts
services/api/app/api/routes/*.py
services/api/app/core/config.py
services/api/app/core/logging.py
services/api/app/db/models.py
services/api/app/main.py
services/api/app/security/*
services/api/migrations/versions/20261108_0007_security_auth.py
services/api/tests/conftest.py
services/api/tests/test_security_auth.py
```

### Commands / results

```text
ruff check services/api workers evals scripts     -> pass
ruff format --check ...                           -> pass
python3 -m mypy                                   -> Success (71 source files)
python3 -m pytest -q                              -> 48 passed
python -m evals.harness                           -> all gates passed (injection green)
compose smoke with Bearer speclens-local-dev-key  -> 401 without key; upload/search/QA/extract OK
```

**Failures:** none.

### Explicit stop

Phase 9 (production UX and deployment) is **not started**. Awaiting explicit approval.

### Remaining risks

1. Bootstrap key is a documented local secret - must be rotated before any shared/hosted deploy.
2. In-process rate limiter is per-API replica (not Redis-backed yet).
3. Retention sweep job is config-only; enforcement is delete API + docs for now.

---

## Phase 9 plan (proposed) - Production UX and deployment

**Do not execute until explicitly approved.**

### Goal

Ship a usable Nuxt frontend for the authenticated API and a reproducible hosted deployment path (Compose/prod images, managed Postgres/Redis/object storage, HTTPS, monitoring, backups) with a resettable public demo on non-confidential docs.

### Scope (in)

1. **Frontend pages:** sign-in (API key / session), workspace dashboard, document library, upload + job progress, document viewer, cited chat, requirements workspace, version compare, eval dashboard, settings/retention.
2. **API client:** contracts package; never embed OpenAI or bootstrap secrets in the browser bundle.
3. **Deployment:** production Docker images; managed Postgres+pgvector; Redis; object storage; API+worker; HTTPS; health/ready probes; error tracking; monitoring.
4. **Ops:** migration/rollback runbook; backup+restore drill; demo reset procedure.

### Non-goals

- Enterprise SSO/SCIM / customer KMS
- Electron packaging (optional later)
- Phase 10 portfolio packaging

### Exit criteria to verify before stop

| Criterion | How we will prove it |
| --- | --- |
| Fresh production deploy from docs | Runbook dry-run in CI or staging |
| Demo resettable safely | Scripted wipe of demo workspace |
| Health + monitoring | Probes + basic metrics/alerts wired |
| Backup restore tested | Documented restore of dump + object store |
| No confidential samples published | Demo corpus review |

### Implementation sketch

1. Branch `cursor/phase9-production-ux-018c` from Phase 8.
2. Nuxt app under `apps/web` against OpenAPI contracts; wire auth header from secure client storage.
3. Prod Compose/image targets + deploy docs; backup/restore verification.
4. Progress update; PR; **stop for Phase 10 approval**.

### Risks for Phase 9

- Frontend scope creep vs thin vertical slices per page.
- Hosting secrets/bootstrap key misuse if demo env shares local defaults.
- Object-store and DB backup consistency during demo reset.
