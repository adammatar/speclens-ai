# SpecLens AI - Progress

## Phase 0-10 + UX redesign + Hebrew + portfolio + MIT

**Status:** Complete on `main` (through PR #20)

---

## Production / eval / UI hardening (active)

**Branch:** `cursor/speclens-production-eval-ui-018c`  
**Base commit reviewed:** `f244972`

### Phase 1 — Citation fail-closed — COMPLETE

**Date:** 2026-11-10

Unsupported answers can no longer be marked `completed` when retrieval returned chunks but zero allow-listed citations survived filtering (including all-forged citations).

### Phase 2 — Production auth & secret safety — COMPLETE

**Date:** 2026-11-10

- Migrations no longer leave the public bootstrap key active (`20261110_0009`).
- Local/CI activate via `python -m app.cli bootstrap-local` / `make bootstrap-local`.
- Hosted startup refuses weak DB passwords, `AUTH_REQUIRED=false`, and an active local bootstrap key.
- Production Compose requires `POSTGRES_PASSWORD` and runs `check-startup` (never bootstrap-local).
- Redis-backed rate limits in hosted mode; local memory fallback when Redis is down.
- CLI: `keys create|list|disable|rotate` (hash-at-rest; plaintext once).

### Phase 3 — Real evaluation harness — COMPLETE

**Date:** 2026-11-10

- Gold datasets no longer contain `predicted_*` values.
- Runtime pipeline (ingest → embed → search → QA/extract/compare) produces predictions.
- Stub mode enforced in CI with Postgres service; live mode optional.
- Regression test: deliberately bad retrieval fails Recall@10 and `--enforce`.
- Reports badge stub/synthetic results and record backends, commit, latencies.

### Phase 4 — Product frontend surfaces — COMPLETE

**Date:** 2026-11-10

- Routes `/requirements`, `/compare`, `/evaluation` with EN/HE + RTL.
- Authenticated `GET /api/v1/evaluation/latest` for the dashboard (no browser FS paths).
- Settings reports deployment mode, auth, providers, retention, security notes.
- Playwright smoke script for core routes; production web build passes.

### Phase 5 — Retention, observability, backup — COMPLETE

**Date:** 2026-11-10

- Retention sweep CLI/Celery with dry-run; destructive mode gated by `RETENTION_SWEEP_ENABLED`.
- Optional Sentry for API/workers with redaction; `X-Request-ID` correlation middleware.
- Readiness checks Redis in hosted mode; backup verify script uses an isolated DB.

Remaining phases (6–8): docs/metadata, security automation, portfolio media — in progress.
