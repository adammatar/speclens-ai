# SpecLens AI - Progress

## Phase 0 - Discovery and architecture

**Status:** Complete (approved)

See `docs/decisions/0001-target-architecture.md`.

---

## Phase 1 - Engineering foundation

**Status:** Complete (approved)

PR: https://github.com/adammatar/speclens-ai/pull/1

---

## Phase 2 - Document ingestion

**Status:** Complete and re-verified. Awaiting merge / explicit approval before Phase 3.

**Date:** 2026-11-08 (re-verified same day)

**PR:** https://github.com/adammatar/speclens-ai/pull/2  
**Branch:** `cursor/phase2-document-ingestion-018c` @ `4f978ab`

### Architecture and implementation decisions

1. Schema: workspaces (default seed), documents, document_versions (SHA-256 dedupe), chunks, ingestion_jobs (`20261108_0002`).
2. Upload returns 202; Celery `speclens.ingest_document` parses/chunks asynchronously.
3. Parsers: Markdown, DOCX, text PDF; reject encrypted/scanned-only PDFs.
4. Section-aware chunking with provenance (heading path, offsets, page).
5. Delete removes DB rows + storage bytes; reprocess enqueues a new job.
6. Worker image installs API package for shared pipeline; no Local Docs Viewer copy.
7. No LangChain; no embeddings yet.

### Acceptance criteria (re-verified)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Non-blocking upload | Yes | 202 + async job success |
| Chunk provenance | Yes | heading_path + offsets asserted |
| SHA-256 dedupe | Yes | HTTP 409 |
| Reprocess / retry | Yes | reprocess job succeeded |
| Delete removes chunks + bytes | Yes | 204; GET/chunks 404 |
| Large synthetic Markdown | Yes | 100-section unit test |
| Alembic head | Yes | `20261108_0002` |
| Synthetic fixtures only | Yes | sample.md / in-memory DOCX/PDF |

### Commands / results (re-run)

```text
ruff + mypy -> pass
pytest -v   -> 15 passed
compose e2e -> upload/reprocess/dedupe/delete ok
```

**Failures:** none.

### Changed files

35 files vs Phase 1 branch (ingestion package, documents routes, migration, worker Dockerfile/tasks, tests, CI, contracts, docs).

### Remaining risks

- Heuristic PDF headings; whitespace token estimates; default workspace stub; published DB/Redis ports for local DX.

### Explicit stop

**Phase 3 not started.** Wait for approval before search/retrieval.

---

## Phase 3 plan (proposed) - Search and retrieval

Do not execute until approved.

### Goals

Batch-embed chunks into pgvector, add Postgres FTS + HNSW, expose hybrid RRF search with workspace filters and a debug endpoint. Keep retrieval independent of generation.

### Tasks

1. Embedder interface + settings (model/dims/batch); secrets server-side only.
2. Migration: vector storage + FTS; HNSW index; filter indexes.
3. Celery embed job after ingest/reprocess (idempotent).
4. Search service: vector top-30 + lexical top-30 -> RRF -> top 12; optional flagged rerank later.
5. APIs: `POST /api/v1/search` and search-debug with document/version/page/section/excerpt/scores.
6. Tests for RRF + workspace isolation; compose smoke; OpenAPI/contracts refresh.
7. Update progress/docs; no LangChain.

### Exit criteria

- Multi-doc search within a workspace
- No cross-workspace leakage
- Provenance fields on every hit
- Retrieval measurable without generation
- CI green; no committed secrets

### Non-goals

Cited QA (Phase 4), extraction (Phase 5), eval harness (Phase 7), real auth (Phase 8), Electron.
