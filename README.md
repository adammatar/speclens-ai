# SpecLens AI

Evaluation-driven AI platform for technical specifications: ingest large docs, retrieve with citations, extract structured requirements, compare versions, and measure quality.

Phase 4 adds cited question answering over hybrid retrieval (stub LLM by default; optional OpenAI Responses API).

## Stack

- **API:** FastAPI, Pydantic settings, SQLAlchemy 2, Alembic, structured JSON logging
- **Worker:** Celery + Redis (`speclens.ingest_document`, `speclens.embed_document_version`)
- **Ingestion:** validate, SHA-256 dedupe, parse, hierarchical chunking, delete/reprocess
- **Retrieval:** stub/OpenAI embeddings, pgvector HNSW, FTS, hybrid RRF search
- **QA:** conversations/messages/citations; stub or OpenAI Responses generator; citation allow-lists
- **Data:** Postgres 16 + pgvector; local filesystem object storage
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
- `POST /api/v1/documents/upload` - accept Markdown/DOCX/PDF and enqueue ingest
- `GET /api/v1/documents/jobs/{job_id}` - ingestion job status
- `GET /api/v1/documents/versions/{id}/chunks` - provenance-preserving chunks
- `POST /api/v1/documents/versions/{id}/reprocess` - retry ingest
- `DELETE /api/v1/documents/{id}` - remove document, chunks, and stored bytes
- `POST /api/v1/search` - hybrid vector + lexical search with RRF
- `POST /api/v1/search/debug` - same results with per-channel ranks
- `POST /api/v1/conversations` - create a cited-QA thread
- `POST /api/v1/conversations/{id}/messages` - ask a question (`stream=true` for SSE)
- `GET /api/v1/conversations/{id}` - messages, citations, retrieval/generation status

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
