# SpecLens AI - Progress

## Phase 0 - Discovery and architecture

**Status:** Complete (approved)

---

## Phase 1 - Engineering foundation

**Status:** Complete (approved) - PR https://github.com/adammatar/speclens-ai/pull/1

---

## Phase 2 - Document ingestion

**Status:** Complete (approved) - PR https://github.com/adammatar/speclens-ai/pull/2

---

## Phase 3 - Search and retrieval

**Status:** Complete on branch (awaiting review / merge; stop before Phase 4)

**Date:** 2026-11-08

**Branch:** `cursor/phase3-search-retrieval-018c`

### Architecture and implementation decisions

1. Stub embedder by default (256-d); optional OpenAI backend when keyed.
2. Migration `20261108_0003`: FTS `search_tsv` + GIN; `chunk_embeddings` + HNSW.
3. Celery embed task chained after successful ingest.
4. Hybrid search: vector + lexical -> RRF; workspace fail-closed.
5. `POST /api/v1/search` and `/search/debug` with provenance fields.
6. No LangChain; rerank flag off.

### Acceptance criteria

| Criterion | Met? |
| --- | --- |
| Workspace-scoped hybrid search | Yes |
| No cross-workspace leakage | Yes |
| Provenance on hits | Yes |
| Retrieval without generation | Yes |
| Embed after ingest | Yes |
| pytest / local smoke | Yes (19 passed) |

### Commands / results

```text
pytest -> 19 passed
ruff + mypy -> pass
alembic -> 20261108_0003
compose search smoke -> hits with rrf_score + debug ranks
```

**Failures:** none.

### Explicit stop

Phase 4 (cited QA) not started - awaiting approval.

### Risks

Stub vs production embed quality; fixed 256-d vectors; English FTS only.

---

## Phase 4 plan (proposed) - Cited question answering

Do not execute until approved.

- Conversations/messages schema
- Context assembly from hybrid search
- Streaming QA with citations only to retrieved chunks
- Insufficient-evidence behavior
- Prompt-injection defenses
- Persist model/prompt/chunk ids/latency/tokens

Non-goals: extraction, eval CI gates, real auth, Electron.
