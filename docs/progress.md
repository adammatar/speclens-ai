# SpecLens AI - Progress

## Phase 0-3

**Status:** Complete (approved) - PRs #1-#3

---

## Phase 4 - Cited question answering

**Status:** Complete on branch (awaiting review / merge; stop before Phase 5)

**Date:** 2026-11-09

**Branch:** `cursor/phase4-cited-qa-018c`

### Architecture and implementation decisions

1. Conversations/messages/citations schema (`20261108_0004`).
2. Prompt `prompts/answering/v1.md`; documents are untrusted data.
3. Context from hybrid search with token budget; stub generator default; optional OpenAI Responses API.
4. Citation allow-list enforcement; insufficient-evidence when retrieval is weak.
5. APIs: create/get conversation; post message (JSON or SSE); status fields for UI.
6. No LangChain; logs omit raw document bodies.

### Acceptance criteria

| Criterion | Met? |
| --- | --- |
| Citations subset of retrieved chunks | Yes |
| Insufficient-evidence path | Yes |
| Retrieval/generation status exposed | Yes |
| Injection phrases not obeyed (stub) | Yes |
| pytest / compose smoke | Yes (23 passed) |

### Commands / results

```text
pytest -> 23 passed
ruff + mypy -> pass
alembic -> 20261108_0004
compose QA smoke -> completed with allow-listed citations
```

**Failures:** none.

### Explicit stop

Phase 5 (requirement extraction) not started - awaiting approval.

### Risks

Stub QA quality; SSE is chunked post-generation; fresh retrieval each turn.

---

## Phase 5 plan (proposed) - Structured requirement intelligence

Do not execute until approved.

- Requirement schema + migration (technical plan Pydantic models)
- Section extraction job with Structured Outputs / stub
- Review states; preserve original model output
- List/filter/edit/export APIs with provenance
- Resumable jobs; synthetic fixtures only

Non-goals: version compare, eval CI gates, real auth.
