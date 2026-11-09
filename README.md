# SpecLens AI

Evaluation-driven AI platform for technical specifications: ingest large docs, retrieve with citations, extract structured requirements, compare versions, and measure quality.

Phase 8 adds API-key auth, workspace RBAC, rate limits, audit events, and log redaction. Local/CI bootstrap key: `speclens-local-dev-key`.

## Stack

- **API:** FastAPI, Pydantic settings, SQLAlchemy 2, Alembic, structured JSON logging
- **Auth:** hashed API keys, workspace roles (owner/editor/viewer), rate limits, audit trail
- **Worker:** Celery + Redis (`speclens.ingest_document`, `speclens.embed_document_version`, `speclens.extract_requirements`, `speclens.compare_document_versions`)
- **Ingestion:** validate, SHA-256 dedupe, parse, hierarchical chunking, delete/reprocess, new document versions
- **Retrieval:** stub/OpenAI embeddings, pgvector HNSW, FTS, hybrid RRF search
- **QA:** conversations/messages/citations; stub or OpenAI Responses generator; citation allow-lists
- **Extraction:** section jobs, Pydantic schema validation, review states, CSV/JSON export
- **Compare:** requirement alignment, change categories, confirm/reject, Jira/test/file links
- **Eval:** JSONL datasets, offline graders, baseline diff, advisory CI thresholds
- **Data:** Postgres 16 + pgvector; local filesystem object storage
- **Web:** `apps/web` placeholder (Nuxt in Phase 9)
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

Authenticated routes require `Authorization: Bearer speclens-local-dev-key` (or `X-API-Key`). Health/ready stay public.

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
- `POST /api/v1/documents/versions/{id}/extractions` - start requirement extraction
- `GET /api/v1/extractions/{job_id}` - extraction job progress (resumable cursor)
- `GET /api/v1/requirements` - list/filter requirements
- `PATCH /api/v1/requirements/{id}` - edit / set review state (preserves original payload)
- `GET /api/v1/requirements/export` - CSV or JSON export
- `POST /api/v1/documents/{id}/versions` - upload a new version of an existing document
- `POST /api/v1/comparisons` - compare requirements between two versions
- `GET /api/v1/comparisons/{job_id}` - comparison status + change list with source quotes
- `PATCH /api/v1/comparisons/changes/{id}` - confirm or reject a detected change

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
| `make eval` | Offline eval harness → `artifacts/eval/report.{json,html}` |

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
