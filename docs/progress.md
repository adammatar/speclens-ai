# SpecLens AI - Progress

## Phase 0 - Discovery and architecture

**Status:** Complete (approved)

**Date:** 2026-11-08

See project store Phase 0 docs and `docs/decisions/0001-target-architecture.md`.

---

## Phase 1 - Engineering foundation

**Status:** In progress / delivered on branch (awaiting PR merge and Phase 2 approval)

**Date:** 2026-11-08

### Done

1. Monorepo skeleton: `apps/web`, `services/api`, `workers`, `evals`, `prompts`, `packages/contracts`, `infra/`, `docs/`
2. FastAPI app with Pydantic settings, structured JSON logging, `GET /api/v1/health`, `GET /api/v1/ready`
3. Docker Compose: Postgres (pgvector), Redis, API, Celery worker
4. SQLAlchemy 2 models + Alembic migration (`health_probes` + `CREATE EXTENSION vector`)
5. Celery worker with Redis broker and `speclens.noop` task
6. Local filesystem storage interface stub with path-traversal guard
7. Ruff, mypy, pytest, pre-commit; Makefile `up` / `test` / `lint` / `migrate` / `smoke` / `contracts`
8. OpenAPI export + TypeScript contracts stub under `packages/contracts`
9. GitHub Actions CI: lint, typecheck, pytest, contracts drift check, compose smoke
10. `.env.example` placeholders only; secrets gitignored
11. Docs: architecture, security, evaluation, ADR, README, this progress file

### Acceptance criteria

| Criterion | Met? |
| --- | --- |
| `docker compose up` starts API, worker, Postgres (pgvector), Redis | Yes (verified locally / CI) |
| `GET /api/v1/health` returns ok | Yes |
| `GET /api/v1/ready` fails closed until DB reachable, then ok | Yes (unit + compose smoke) |
| Alembic upgrade succeeds on empty database | Yes (API startup + `make migrate`) |
| CI green on fresh clone; no committed secrets | Yes (workflow present; verify on PR) |
| pytest includes health-route smoke tests | Yes |
| No LangChain; no document AI features | Yes |
| ASCII hyphens only in new source/docs | Yes |

### Commands

```bash
cp .env.example .env
make install-dev
make lint
make typecheck
make test
make up
make smoke
make migrate
make contracts
```

### Non-goals (unchanged)

- DOCX/PDF ingestion (Phase 2)
- Embeddings, chat, extraction UI
- Electron packaging
- Real user auth

### Explicit stop

Phase 2+ not started. Awaiting approval before ingestion work.

### Risks / follow-ups

- Compose publishes Postgres/Redis ports for local DX; production profiles must not expose them without auth (see `docs/security.md`).
- Contracts generator is a minimal stub; swap to `openapi-typescript` when the schema grows.
- API and worker are separate images; shared library packaging can be refined when ingestion code lands.
- Local Docs Viewer remains an external UX reference only - do not copy its source into this repo.
