# SpecLens AI - Progress

## Phase 0 - Discovery and architecture

**Status:** Complete (approved)

**Date:** 2026-11-08

See `docs/decisions/0001-target-architecture.md`, `docs/architecture.md`, and `docs/security.md`.

---

## Phase 1 - Engineering foundation

**Status:** Complete and verified (CI green). Awaiting merge / explicit approval before Phase 2.

**Date:** 2026-11-08 (re-verified same day)

**PR:** https://github.com/adammatar/speclens-ai/pull/1  
**Branch:** `cursor/phase1-engineering-foundation-018c` @ `81fa337`

### Architecture and implementation decisions

1. **Greenfield monorepo** (ADR 0001). Local Docs Viewer is UX/parsing reference only; no source copied.
2. **FastAPI** under `services/api`: Pydantic Settings, structured JSON logging, `/api/v1/health` (liveness) and `/api/v1/ready` (DB readiness, 503 until reachable).
3. **Postgres 16 + pgvector** in Compose; SQLAlchemy 2; Alembic creates `vector` extension and `health_probes`.
4. **Celery + Redis** persistent queue; `speclens.noop` proves dequeue/ack.
5. **Filesystem `StorageInterface` stub** with path-traversal guard (object store later).
6. **OpenAPI -> TypeScript contracts stub** in `packages/contracts`.
7. **Ruff, mypy, pytest, pre-commit**, Makefile, GitHub Actions (lint/typecheck/pytest + compose smoke).
8. **No LangChain**; no document AI features yet; ASCII hyphens in prose.

### Acceptance criteria (re-verified)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Compose starts API, worker, Postgres (pgvector), Redis | Yes | Four services up; healthchecks green |
| `GET /api/v1/health` returns ok | Yes | `{"status":"ok"}` |
| `GET /api/v1/ready` fails closed until DB up, then ok | Yes | Unit 503 mock; live ready ok |
| Alembic upgrade on empty DB | Yes | `20261108_0001`; `health_probes` + `vector` |
| CI green; no committed secrets | Yes | PR 2/2 pass; empty `OPENAI_API_KEY` |
| pytest health-route smoke | Yes | 6 passed |
| No LangChain; no document AI | Yes | Non-goal only; no dependency |
| ASCII hyphens | Yes | Em-dashes normalized |

### Commands and test results (re-run)

```text
ruff check / format --check     -> pass
mypy                            -> Success (17 files)
pytest -v                       -> 6 passed
compose up --build              -> api/worker/postgres/redis up
curl /api/v1/health|/ready      -> ok
alembic current                 -> 20261108_0001 (head)
Celery noop                     -> ok
gh pr checks                    -> both jobs pass
```

**Failures:** none.

### Changed files (63 vs `main`)

See PR diff. Major paths: `services/api/**`, `workers/**`, `infra/compose.yaml`, `packages/contracts/**`, `docs/**`, `.github/workflows/ci.yml`, `Makefile`, `.env.example`, `README.md`.

### Remaining risks

- Published Postgres/Redis ports are for local DX only.
- Some agent VMs need `bridge-nf-call-iptables=0` for Compose bridge traffic.
- Contracts generator is a stub until schema growth.
- Shared ingestion packaging across API/worker still TBD for Phase 2.

### Explicit stop

**Phase 2 not started.** Wait for explicit approval before ingestion work.

---

## Phase 2 plan (proposed) - Document ingestion

Do not execute until approved.

### Goals

Upload and process DOCX, text-based PDF, and Markdown asynchronously; every chunk keeps full provenance.

### Tasks

1. Schema: documents, document_versions, chunks, job status; Alembic migration.
2. Upload API: validation, SHA-256 dedupe, storage write, enqueue ingest job.
3. Parsers for DOCX / text PDF / Markdown with section paths and offsets; reject encrypted/scanned-only PDFs.
4. Hierarchical chunking (600-900 tokens, 80-120 overlap; heading path on every chunk).
5. Celery ingest jobs with progress, failure, retry.
6. Delete and reprocess workflows (remove bytes + chunks).
7. Tests with synthetic fixtures only (no confidential customer docs).
8. Refresh OpenAPI/contracts and CI.

### Exit criteria

- Large document processes without blocking the API
- Every chunk traces to source
- Duplicate uploads detected
- Failed jobs retryable
- Delete removes derived rows (embeddings arrive in Phase 3)

### Non-goals for Phase 2

- Embeddings/search, cited QA, requirement extraction, real auth, Electron, copying Local Docs Viewer source
