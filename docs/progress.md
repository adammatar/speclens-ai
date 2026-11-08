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

**Status:** Complete on branch (awaiting review / merge; stop before Phase 3)

**Date:** 2026-11-08

**Branch:** `cursor/phase2-document-ingestion-018c`

### Architecture and implementation decisions

1. Schema: workspaces (default seed), documents, document_versions (SHA-256 dedupe), chunks, ingestion_jobs.
2. Upload returns 202; Celery `speclens.ingest_document` parses and chunks asynchronously.
3. Parsers for Markdown, DOCX, text PDF; reject encrypted/scanned-only PDFs.
4. Section-aware chunking with provenance (heading path, offsets, page).
5. Delete removes DB rows + storage bytes; reprocess enqueues a new job.
6. Worker image installs the API package for shared pipeline code.
7. No LangChain; no embeddings yet.

### Acceptance criteria

| Criterion | Met? |
| --- | --- |
| Non-blocking upload | Yes |
| Chunk provenance | Yes |
| SHA-256 dedupe (409) | Yes |
| Reprocess / retry | Yes |
| Delete removes chunks + bytes | Yes |
| Large synthetic Markdown chunks | Yes |
| Synthetic fixtures only | Yes |

### Commands / results

```text
pytest -> 15 passed
ruff + mypy -> pass
compose upload smoke -> job succeeded, 4 chunks, dedupe 409, delete 204
```

**Failures:** none.

### Explicit stop

Phase 3 (search/retrieval) not started - awaiting approval.

### Risks

- Heuristic PDF headings; whitespace token estimates; default workspace stub only.

---

## Phase 3 plan (proposed) - Search and retrieval

Do not execute until approved.

- Batch embeddings into pgvector; FTS + HNSW
- Hybrid RRF search API with workspace filters
- Search-debug scores/metadata
- Tests + CI smoke

Non-goals: cited QA, extraction, real auth.
