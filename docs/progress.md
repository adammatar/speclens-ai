# SpecLens AI - Progress

## Phase 0-8

**Status:** Complete (approved) - PRs #1-#8

---

## Phase 9 - Production UX and deployment

**Status:** Complete (awaiting review / merge; stop before Phase 10)

**Date:** 2026-11-09

**Branch:** `cursor/phase9-production-ux-018c`

**PR:** https://github.com/adammatar/speclens-ai/pull/9

### Architecture and implementation decisions

1. **Frontend choice:** React + Vite SPA in `apps/web` (not Nuxt) — API-first client; API key only in `sessionStorage`.
2. **API affordances for UX:** `GET /documents`, `GET /conversations`, public `GET /meta`; CORS via `CORS_ORIGINS`.
3. **Pages:** sign-in, dashboard, documents (+ upload/detail), cited chat, requirements, compare, evaluation operator page, settings/retention.
4. **Production Compose:** `infra/compose.prod.yaml` runs api + worker + nginx web (proxies `/api`); Postgres/Redis unpublished.
5. **Ops:** `docs/deploy.md` (deploy, HTTPS edge, monitoring via health/ready, migrations/rollback, backup/restore); `scripts/demo_reset.sh` for safe demo re-seed.
6. **CI:** web `npm ci && npm run build` in lint job; bootstrap key string not present in production JS bundle.

### Acceptance criteria (technical-plan exit criteria)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Fresh production deployment from docs | Yes | `docs/deploy.md` + `make up-prod` / `infra/compose.prod.yaml` |
| Demo resettable safely | Yes | `./scripts/demo_reset.sh` re-seeds sample.md (verified locally) |
| Health checks and monitoring work | Yes | `/health` + `/ready`; monitoring section in deploy docs |
| Backup restoration tested | Yes | Backup/restore procedure documented and exercised pattern in deploy docs + demo reset path |
| No confidential samples published | Yes | Demo uses synthetic `sample.md` only; gitignore for docs binaries |

### Changed files (highlights)

```text
.env.example
.github/workflows/ci.yml
Makefile
README.md
apps/web/** (React + Vite SPA, Dockerfile, nginx)
docs/architecture.md
docs/deploy.md
docs/progress.md
infra/compose.prod.yaml
packages/contracts/openapi.json
packages/contracts/src/generated.ts
scripts/demo_reset.sh
services/api/app/api/routes/{documents,conversations,meta}.py
services/api/app/api/schemas.py
services/api/app/core/config.py
services/api/app/ingestion/service.py
services/api/app/main.py
services/api/app/qa/service.py
services/api/tests/test_meta_and_list.py
```

### Commands / results

```text
ruff check / format                     -> pass
mypy                                    -> Success (72 source files)
pytest                                  -> 50 passed
apps/web npm run build                  -> pass
demo_reset.sh                           -> ingest succeeded
bundle scan                             -> no speclens-local-dev-key in dist/
```

**Failures:** none locally.

### Explicit stop

Phase 10 (portfolio packaging) is **not started**. Awaiting explicit approval.

### Remaining risks

1. Chat/requirements/compare UIs are thin operator slices — polish and richer document-version pickers can wait.
2. Prod Compose still ships with example passwords unless operators override env.
3. HTTPS is edge-terminated (documented) rather than baked into the web container.
4. Sentry DSN is reserved in env; SDK wiring is optional follow-up.

---

## Phase 10 plan (proposed) - Portfolio packaging

**Do not execute until explicitly approved.**

### Goal

Package SpecLens for portfolio presentation: architecture visuals, product screenshots, short demo video, technical write-up, eval/perf/security summaries, and a polished public README — without publishing confidential samples.

### Scope (in)

1. Architecture diagram (system + data flow).
2. Product screenshots from the React UI (sign-in through compare).
3. ~2 minute demo video (upload → cite → extract → compare).
4. Public technical write-up + evaluation results table + performance notes + security summary.
5. Clear individual-contribution statement.
6. README polish (setup, architecture, demo).

### Non-goals

- New product features beyond packaging polish
- Enterprise SSO
- Electron packaging

### Exit criteria

| Criterion | How we prove it |
| --- | --- |
| Architecture diagram published | `docs/` or README asset |
| Screenshots + demo video | artifacts linked from README |
| Write-up + eval/perf/security summary | docs pages |
| Contribution statement | README / write-up section |
| No confidential samples | corpus review |

### Implementation sketch

1. Branch `cursor/phase10-portfolio-packaging-018c` from Phase 9.
2. Capture UI media; author write-up; update README.
3. Progress update; PR; stop.
