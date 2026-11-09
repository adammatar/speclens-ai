# SpecLens AI - Progress

## Phase 0-3

**Status:** Complete (approved) - PRs #1-#3

---

## Phase 4 - Cited question answering

**Status:** Complete and re-verified (awaiting review / merge; stop before Phase 5)

**Date:** 2026-11-09

**Branch:** `cursor/phase4-cited-qa-018c`

**PR:** https://github.com/adammatar/speclens-ai/pull/4

### Architecture and implementation decisions

1. **Persistence:** Alembic `20261108_0004` adds `conversations`, `messages`, and `message_citations` with retrieval/generation status, model, prompt version, token/latency fields, and claim-indexed citations.
2. **Prompt pack:** `prompts/answering/v1.md` treats uploaded document text as untrusted data; instructs allow-listed citations and insufficient-evidence abstention.
3. **Context assembly:** Hybrid search hits packed under `qa_context_token_budget` / `qa_max_context_chunks` / `qa_min_rrf_score`; empty or weak retrieval fails closed to insufficient evidence.
4. **Generators:** Default stub for CI/local; optional OpenAI Responses API behind `generation_backend`. Both receive an allow-list; `filter_citations` drops any foreign chunk IDs before persist.
5. **API:** `POST/GET /api/v1/conversations`, `POST .../messages` (JSON or SSE). Responses expose `status`, `retrieval_status`, `generation_status`, retrieved and citation chunk IDs.
6. **Safety / ops:** No LangChain; structured logs omit raw document bodies and full prompts; workspace scoping rejects foreign version filters.

### Acceptance criteria (technical-plan exit criteria)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Every answer contains valid source references (citations ⊆ retrieved) | Yes | `filter_citations`; `test_citations_filter`; `test_qa_turn_cites_only_retrieved_chunks`; live smoke; CI compose assert |
| Unsupported questions → explicit insufficient-evidence | Yes | `evidence_is_sufficient` + generator/model paths set `MessageStatus.INSUFFICIENT_EVIDENCE` |
| Retrieval and generation status exposed for UI | Yes | Message + AnswerTurn fields; SSE `retrieval`/`generation` events |
| Documents are data, not instructions (injection defenses) | Yes | Prompt rules; stub ignores injection phrasing / forged IDs (`test_stub_generator_ignores_injection_and_forged_citations`) |
| Conversation + message persistence; streaming endpoint | Yes | Models + routes; SSE path (post-computed token chunks) |
| Clicking citation opens page/section | Deferred to UI | API returns `chunk_id` + `source_quote`; page/heading available via chunk/search APIs (no product UI in this phase) |

### Changed files (vs Phase 3 branch)

```text
.env.example
.github/workflows/ci.yml
README.md
docs/progress.md
packages/contracts/openapi.json
packages/contracts/src/generated.ts
prompts/answering/v1.md
services/api/app/api/routes/conversations.py
services/api/app/api/schemas.py
services/api/app/core/config.py
services/api/app/db/models.py
services/api/app/generation/__init__.py
services/api/app/generation/base.py
services/api/app/generation/citations.py
services/api/app/generation/factory.py
services/api/app/generation/openai_backend.py
services/api/app/generation/stub.py
services/api/app/main.py
services/api/app/qa/__init__.py
services/api/app/qa/context.py
services/api/app/qa/service.py
services/api/migrations/versions/20261108_0004_cited_qa.py
services/api/tests/test_citations_filter.py
services/api/tests/test_qa_service.py
```

### Commands / results (re-verification 2026-11-09)

```text
cd services/api && ruff check app tests     -> All checks passed! (exit 0)
cd services/api && mypy app                 -> Success: no issues found in 49 source files (exit 0)
cd services/api && pytest -q                -> 22 passed, 0 failed (exit 0)
Live compose API smoke (upload→ingest→ready→conversation message):
  status=completed, retrieval_status=succeeded, generation_status=succeeded
  citation_chunk_ids ⊆ retrieved_chunk_ids  -> SMOKE_OK
CI (PR #4): Lint/typecheck/pytest SUCCESS; Compose smoke was in progress at verify time
```

**Failures:** none.

### Explicit stop

Phase 5 (structured requirement intelligence) is **not started**. Awaiting explicit approval.

### Remaining risks

1. Stub QA is not production answer quality; OpenAI path is optional and untested in CI without keys.
2. SSE streams after the full answer is computed (progress UX only, not true token streaming).
3. Fresh retrieval each turn; stub largely ignores prior conversation turns.
4. Citation navigation UX (page/section jump) awaits a frontend; API surface is chunk-id based.
5. Completed answers with stripped citations can still surface if the model invents none but leaves prose (mitigated by stub always citing allow-listed hits when evidence exists).

---

## Phase 5 plan (proposed) - Structured requirement intelligence

**Do not execute until explicitly approved.**

### Goal

Extract structured requirements from ingested document sections with mandatory schema validation, provenance, human review states, and CSV/JSON export - stub-first for CI, optional Structured Outputs when keys exist.

### Scope (in)

1. **Schema + migration**
   - Pydantic models matching technical plan: `SourceReference`, `AcceptanceCriterion`, `Requirement` (types, priority, confidence, dependencies, ambiguities, sources).
   - Tables for extraction jobs, requirements, review state, and immutable original model payload.
2. **Extraction job**
   - Section-oriented worker (Celery) over ready document versions.
   - Stub extractor for CI/local; optional OpenAI Structured Outputs backend.
   - Resumable after failure (job progress + section cursor).
3. **Review workflow**
   - States: `proposed`, `accepted`, `edited`, `rejected`.
   - Edits preserve original model output; accepted edits flagged as future eval examples.
4. **APIs**
   - Start/list extraction jobs; list/filter/edit requirements; CSV + JSON export.
   - Every field carries source quote / section / page provenance where available.
5. **Tests + CI**
   - Schema validation tests; stub extraction on synthetic fixtures only; compose smoke for one extract + export.
   - Contracts regen; ASCII hyphens; no LangChain; no confidential fixtures.

### Non-goals (this phase)

- Version comparison / change classification (Phase 6)
- Eval harness CI gates / gold sets beyond "accepted edits become examples" storage hooks (Phase 7+)
- Real multi-user auth / workspaces beyond existing default workspace
- Product UI table (API + OpenAPI sufficient; UI later)

### Exit criteria to verify before stop

| Criterion | How we will prove it |
| --- | --- |
| Schema validation mandatory | Invalid payloads rejected in API/tests |
| Every extracted requirement has a source quote | Stub + filter; pytest assert |
| Edit without losing original model output | Persist `original_payload` + edited fields; test |
| Extraction resumable after failure | Job status/cursor; failure-then-resume test or smoke |
| Filter + CSV/JSON export | API tests / compose smoke |

### Implementation sketch

1. Branch `cursor/phase5-requirement-extraction-018c` from Phase 4 branch.
2. Models/migration `20261108_0005` (+ enums for type/priority/review).
3. `prompts/extraction/v1.md` + `app/extraction/**` (stub + optional OpenAI).
4. Celery task hooked after ingest/embed or explicit "extract" API.
5. Routes under `/api/v1/requirements` and `/api/v1/documents/.../extractions`.
6. Update CI compose smoke; regenerate OpenAPI/TS contracts; update this progress file; open PR; **stop for Phase 6 approval**.

### Risks for Phase 5

- Section boundary quality depends on Phase 2 chunk/heading paths.
- Stub extractions will be heuristic; real LLM quality needs keys + later eval.
- Contradiction detection may be best-effort / deferred if not reliably stubbable.
