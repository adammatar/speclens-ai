# SpecLens AI

Evaluation-driven AI platform for technical specifications: ingest large docs, retrieve with citations, extract structured requirements, compare versions, and measure quality.

Phase 1 delivers the engineering foundation only (API, worker, Postgres/pgvector, Redis, tooling, CI). No document AI features yet.

## Stack

- **API:** FastAPI, Pydantic settings, SQLAlchemy 2, Alembic, structured JSON logging
- **Worker:** Celery + Redis (persistent queue) with a no-op job
- **Data:** Postgres 16 + pgvector; local filesystem storage interface stub
- **Web:** `apps/web` placeholder (Nuxt in a later phase)
- **Contracts:** OpenAPI export to TypeScript under `packages/contracts`
- **Tooling:** Ruff, mypy, pytest, pre-commit, Make, GitHub Actions

Python **>= 3.12**. Node.js **>= 22** (contracts package).

## Quick start (Docker Compose)

```bash
cp .env.example .env
make up          # builds and starts postgres, redis, api, worker
make smoke       # health + ready checks
```

API docs (local): http://127.0.0.1:8000/docs

- `GET /api/v1/health` - liveness
- `GET /api/v1/ready` - readiness (fails closed until Postgres is reachable)

Migrations run automatically on API container start (`alembic upgrade head`). To run manually:

```bash
make migrate
```

## Local Python development

```bash
python3 -m venv .venv
source .venv/bin/activate
make install-dev
make lint
make typecheck
make test
```

Regenerate OpenAPI + TypeScript stubs:

```bash
make contracts
```

## Make targets

| Target | Purpose |
| --- | --- |
| `make up` | Start Compose stack |
| `make down` | Stop stack and remove volumes |
| `make migrate` | Alembic upgrade via Compose |
| `make test` | pytest |
| `make lint` | Ruff check + format check |
| `make typecheck` | mypy |
| `make contracts` | Export OpenAPI and generate TS stubs |
| `make smoke` | Compose up + health/ready curl checks |

## Repository layout

See `docs/architecture.md`. ADR: `docs/decisions/0001-target-architecture.md`.

## Prototype note

Local Docs Viewer (private offline DOCX viewer) is a UX/parsing reference only. Its source is **not** copied into this repository.

## Security

- Never commit secrets; use `.env.example` placeholders only.
- Uploaded documents are untrusted data (see `docs/security.md`).
- No LangChain dependency.

## License

Proprietary - private repository.
