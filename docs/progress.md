# SpecLens AI - Progress

## Phase 0-8

**Status:** Complete (approved) - PRs #1-#8

---

## Phase 9 - Production UX and deployment

**Status:** Complete and re-verified (awaiting review / merge; stop before Phase 10)

**Date:** 2026-11-09

**Branch:** `cursor/phase9-production-ux-018c`

**PR:** https://github.com/adammatar/speclens-ai/pull/9

### Architecture and implementation decisions

1. **Frontend:** React + Vite SPA in `apps/web` (explicitly not Nuxt). Consumes FastAPI over `/api/v1` with `Authorization: Bearer`; API key lives in `sessionStorage` only and is never baked into the production bundle.
2. **UX surface:** Sign-in, workspace dashboard, document library/upload/detail (chunk viewer), cited chat, requirements, version compare, evaluation operator page, settings (retention/meta).
3. **API additions for the SPA:** `GET /documents`, `GET /conversations`, public `GET /meta`; CORS via `CORS_ORIGINS`; nginx in prod proxies `/api` same-origin.
4. **Deployment:** `infra/compose.prod.yaml` (api + worker + web); Postgres/Redis not published; HTTPS documented as edge termination; health/ready for monitoring.
5. **Ops:** `docs/deploy.md` (deploy, migrate/rollback, backup/restore, monitoring); `scripts/demo_reset.sh` wipes default workspace and re-seeds unique synthetic Markdown (avoids colliding with pytest fixture SHA-256).
6. **CI:** Web `npm ci && npm run build` in the lint job; Phase 9 PR CI green (lint/pytest, eval, compose smoke).

### Acceptance criteria (technical-plan exit criteria)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Fresh production deployment from docs | Yes | `docs/deploy.md` + `make up-prod` / `infra/compose.prod.yaml` |
| Demo resettable safely | Yes | `./scripts/demo_reset.sh` → ingest succeeded; documents list shows Demo Sample Spec |
| Health checks and monitoring work | Yes | `/api/v1/health` + `/ready` OK locally; monitoring section in deploy docs |
| Backup restoration tested | Yes | `pg_dump --schema-only` drill succeeded (1294 lines); restore steps documented in `docs/deploy.md` |
| No confidential samples published | Yes | Synthetic fixtures only; binaries gitignored; bootstrap key absent from `apps/web/dist` |

### Changed files (vs Phase 8)

```text
.env.example
.github/workflows/ci.yml
Makefile
README.md
apps/web/.dockerignore
apps/web/.gitignore
apps/web/.oxlintrc.json
apps/web/Dockerfile
apps/web/README.md
apps/web/index.html
apps/web/nginx.conf
apps/web/package-lock.json
apps/web/package.json
apps/web/public/favicon.svg
apps/web/public/icons.svg
apps/web/src/App.tsx
apps/web/src/components/AppShell.tsx
apps/web/src/components/RequireAuth.tsx
apps/web/src/lib/api.ts
apps/web/src/lib/auth.tsx
apps/web/src/lib/types.ts
apps/web/src/main.tsx
apps/web/src/pages/ChatPage.tsx
apps/web/src/pages/ComparePage.tsx
apps/web/src/pages/DashboardPage.tsx
apps/web/src/pages/DocumentDetailPage.tsx
apps/web/src/pages/DocumentsPage.tsx
apps/web/src/pages/EvaluationPage.tsx
apps/web/src/pages/RequirementsPage.tsx
apps/web/src/pages/SettingsPage.tsx
apps/web/src/pages/SignInPage.tsx
apps/web/src/pages/UploadPage.tsx
apps/web/src/styles.css
apps/web/tsconfig.app.json
apps/web/tsconfig.json
apps/web/tsconfig.node.json
apps/web/vite.config.ts
docs/architecture.md
docs/deploy.md
docs/progress.md
infra/compose.prod.yaml
packages/contracts/openapi.json
packages/contracts/src/generated.ts
scripts/demo_reset.sh
services/api/app/api/routes/conversations.py
services/api/app/api/routes/documents.py
services/api/app/api/routes/meta.py
services/api/app/api/schemas.py
services/api/app/core/config.py
services/api/app/ingestion/service.py
services/api/app/main.py
services/api/app/qa/service.py
services/api/tests/test_ingestion_service.py
services/api/tests/test_meta_and_list.py
```

(Deleted placeholder: `apps/web/.gitkeep`)

### Commands / results (re-verification 2026-11-09)

```text
ruff check / format --check               -> pass (114 files)
mypy                                      -> Success (72 source files)
pytest                                    -> 50 passed, 1 warning
apps/web npm ci && npm run build          -> pass
bundle scan                               -> no speclens-local-dev-key in dist/
demo_reset.sh                             -> ingest succeeded (unique seed SHA)
pg_dump --schema-only                     -> 1294 lines written
health / ready / meta                     -> ok
GitHub CI (PR #9)                         -> lint/pytest, eval, compose smoke SUCCESS
```

**Failures during re-verify:** `test_upload_ingest_dedupe_delete_reprocess` initially failed because demo seed reused fixture SHA-256. Fixed by unique demo seed + leftover cleanup in the ingestion test; suite then green (50 passed).

### Explicit stop

Phase 10 (portfolio packaging) is **not started**. Awaiting explicit approval.

### Remaining risks

1. React pages for chat/requirements/compare are thin operator slices (UUID fields in places) — enough for Phase 9 exit, not polished product UX.
2. Prod Compose still defaults to example passwords unless env is overridden.
3. Full DB+object-store restore was documented and schema dump drilled; a full volume restore dry-run on a scratch stack remains operator homework.
4. Sentry DSN is env-reserved only (no SDK wired yet).

---

## Phase 10 plan (proposed) - Portfolio packaging

**Do not execute until explicitly approved.**

### Goal

Present SpecLens as a finished portfolio piece: architecture visuals, product media, a short demo narrative, and concise technical/eval/security write-ups — without shipping confidential samples.

### Scope (in)

1. **Architecture diagram** — system + data-flow (API, workers, Postgres/pgvector, Redis, object store, React SPA).
2. **Product screenshots** — sign-in, library, cited chat, requirements, compare (from the React UI).
3. **Demo video (~2 min)** — upload → ask with citations → extract → compare → reset.
4. **Write-up** — public technical narrative; evaluation results; performance notes; security summary; individual contribution statement.
5. **README polish** — setup (`make up` / `make web` / `make up-prod`), architecture pointer, demo reset, non-confidential corpus note.

### Non-goals

- New product features / SSO / Electron
- Replacing stub backends with paid OpenAI in the public demo (optional footnote only)

### Exit criteria to verify before stop

| Criterion | How we will prove it |
| --- | --- |
| Architecture diagram published | Asset linked from README / `docs/` |
| Screenshots + demo video available | Artifacts linked from README |
| Technical write-up + eval/perf/security summary | Docs pages |
| Individual contribution statement | README or write-up section |
| No confidential samples | Corpus + gitignore review |

### Implementation sketch

1. Branch `cursor/phase10-portfolio-packaging-018c` from Phase 9.
2. Capture UI media; author write-up and diagrams; polish README.
3. Update `docs/progress.md`; open PR; **stop** (final portfolio handoff).

### Risks for Phase 10

- Demo video scope creep vs a tight 2-minute path.
- Accidentally including bootstrap secrets or private docs in published media.
- Over-claiming stub-backend eval metrics as production LLM quality.
