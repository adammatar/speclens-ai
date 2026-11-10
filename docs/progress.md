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

Remaining phases (3–8): real eval runner, product UI, retention/observability, docs, security automation, portfolio media — in progress.
