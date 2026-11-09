# SpecLens AI - Progress

## Phase 0 - Discovery and architecture

**Status:** Complete (approved)

---

## Phase 1 - Engineering foundation

**Status:** Complete (approved) - https://github.com/adammatar/speclens-ai/pull/1

---

## Phase 2 - Document ingestion

**Status:** Complete (approved) - https://github.com/adammatar/speclens-ai/pull/2

---

## Phase 3 - Search and retrieval

**Status:** Complete and re-verified; CI green. Awaiting merge / explicit approval before Phase 4.

**Date:** 2026-11-08 (re-verified same day)

**PR:** https://github.com/adammatar/speclens-ai/pull/3  
**Branch:** `cursor/phase3-search-retrieval-018c` @ `1e33bf8`

### Architecture and implementation decisions

1. Stub embedder default (256-d); optional OpenAI backend when keyed.
2. Migration `20261108_0003`: FTS `search_tsv` + GIN; `chunk_embeddings` + HNSW.
3. Celery embed chained after successful ingest.
4. Hybrid search: vector + lexical -> RRF; workspace fail-closed.
5. `POST /api/v1/search` and `/search/debug` with provenance fields.
6. No LangChain; rerank flag off.

### Acceptance criteria (re-verified)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Workspace-scoped hybrid search | Yes | Compose search hit with provenance |
| No cross-workspace leakage | Yes | unknown WS HTTP 400 |
| Provenance on hits | Yes | ids, heading_path, excerpt, offsets |
| Retrieval without generation | Yes | stub + FTS/RRF |
| Embed after ingest | Yes | embeddings count > 0 |
| Tests / CI | Yes | pytest 19 passed; PR CI 2/2 green |

### Commands / results (re-run)

```text
ruff + mypy -> pass
pytest -v   -> 19 passed
alembic     -> 20261108_0003
compose     -> upload/embed/search/debug ok; unknown WS 400
```

**Failures:** none.

### Changed files

28 files vs Phase 2 (embeddings, retrieval, search routes, migration, tests, CI, contracts, docs).

### Remaining risks

Stub vs production embed quality; fixed 256-d schema; English FTS only; rerank not implemented.

### Explicit stop

**Phase 4 not started.** Wait for approval before cited QA.

---

## Phase 4 plan (proposed) - Cited question answering

Do not execute until approved.

### Goals

Streaming citation-grounded QA over hybrid retrieval, with conversations, insufficient-evidence behavior, and prompt-injection defenses. Documents are untrusted data.

### Tasks

1. Conversations/messages/citations schema + migration
2. Versioned answering prompts under `prompts/answering/`
3. Context assembly from Phase 3 search with token budget
4. Streaming Responses API endpoint; citations allow-listed to retrieved chunk ids; stub LLM for tests
5. Insufficient-evidence path; follow-up turns
6. Persist model/prompt_version/chunk ids/latency/tokens; no raw doc bodies in logs
7. Prompt-injection + citation allow-list tests; OpenAPI/CI updates

### Exit criteria

- Citations only to retrieved chunks
- Explicit insufficient-evidence when unsupported
- Retrieval/generation status exposed via API
- CI green; no committed secrets

### Non-goals

Extraction, version compare, eval CI gates, real auth, Electron.
