# SpecLens AI - Progress

## Phase 0-4

**Status:** Complete (approved) - PRs #1-#4

---

## Phase 5 - Structured requirement intelligence

**Status:** Complete and re-verified (awaiting review / merge; stop before Phase 6)

**Date:** 2026-11-09

**Branch:** `cursor/phase5-requirement-extraction-018c`

**PR:** https://github.com/adammatar/speclens-ai/pull/5

### Architecture and implementation decisions

1. **Schema:** Pydantic `SourceReference` / `AcceptanceCriterion` / `RequirementDraft` with mandatory non-empty `source_quote`; re-validated on persist and edit.
2. **Persistence:** Alembic `20261108_0005` adds `extraction_jobs` (section cursor, progress) and `requirements` (review state, immutable `original_payload`, `is_eval_example`).
3. **Extraction:** Section-grouped chunks; stub heuristic modal extractor default; optional OpenAI Structured Outputs via urllib Responses API.
4. **Resumability:** Jobs advance `section_cursor` per section; failures persist cursor; re-run continues from cursor.
5. **Review:** States `proposed` / `edited` / `accepted` / `rejected`; edits never mutate `original_payload`; `accepted` sets `is_eval_example`.
6. **APIs:** start extraction, job status, list/filter, patch, CSV/JSON export. Celery task `speclens.extract_requirements`.
7. **Safety:** No LangChain; prompts treat docs as data; logs omit raw document bodies; synthetic fixtures only.

### Acceptance criteria (technical-plan exit criteria)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Schema validation mandatory | Yes | `RequirementDraft` + persist/edit re-validate; `test_extraction_schema` |
| Every extracted requirement has a source quote | Yes | Stub + schema; pipeline/CI/live smoke asserts |
| Edit without losing original model output | Yes | `original_payload` immutable; pipeline + live smoke |
| Accepted human edits become evaluation examples | Yes | `is_eval_example=True` on `accepted` |
| Extraction resumable after failure | Yes | `fail_after_sections` resume test |
| List/filter + CSV/JSON export | Yes | export tests; live CSV/JSON smoke; CI compose |

### Changed files (vs Phase 4)

```text
.env.example
.github/workflows/ci.yml
README.md
docs/progress.md
packages/contracts/openapi.json
packages/contracts/src/generated.ts
prompts/extraction/v1.md
services/api/app/api/routes/requirements.py
services/api/app/api/schemas.py
services/api/app/core/config.py
services/api/app/db/models.py
services/api/app/extraction/__init__.py
services/api/app/extraction/base.py
services/api/app/extraction/factory.py
services/api/app/extraction/openai_backend.py
services/api/app/extraction/pipeline.py
services/api/app/extraction/schema.py
services/api/app/extraction/service.py
services/api/app/extraction/stub.py
services/api/app/ingestion/queue.py
services/api/app/main.py
services/api/migrations/versions/20261108_0005_requirement_extraction.py
services/api/tests/test_extraction_pipeline.py
services/api/tests/test_extraction_schema.py
workers/speclens_worker/tasks.py
```

### Commands / results (re-verification 2026-11-09)

```text
cd services/api && ruff check app tests     -> All checks passed! (exit 0)
cd services/api && mypy app                 -> Success: no issues found in 58 source files (exit 0)
cd services/api && python3 -m pytest -q     -> 29 passed, 0 failed (exit 0)
alembic current                             -> 20261108_0005 (head)
Live compose re-smoke:
  extract succeeded; 5 requirements with source quotes;
  accept preserves original_payload + is_eval_example;
  CSV export OK -> REVERIFY_SMOKE_OK
CI (PR #5): Lint/typecheck/pytest SUCCESS; Compose smoke SUCCESS
```

**Failures:** none.

### Explicit stop

Phase 6 (version comparison / traceability) is **not started**. Awaiting explicit approval.

### Remaining risks

1. Stub extraction is heuristic (shall/must/should); OpenAI path optional and untested in CI without keys.
2. Contradiction candidates are schema-ready but stub rarely fills them.
3. Section boundaries follow `heading_path` groups from Phase 2 chunking quality.
4. No product UI table yet (API + OpenAPI only).

---

## Phase 6 plan (proposed) - Version comparison and traceability

**Do not execute until explicitly approved.**

### Goal

Compare extracted requirements across two document versions: align counterparts, classify changes, expose side-by-side sources, support confirm/reject, and attach light traceability links.

### Scope (in)

1. **Compare job + schema**
   - Migration for `comparison_jobs` / `requirement_changes` (old/new requirement IDs, category, old/new quotes, decision state).
   - Change categories from technical plan: added, removed, clarified, behavior changed, priority changed, acceptance criteria changed, potential breaking change, uncertain.
2. **Alignment**
   - Match by `external_id` when present; otherwise text/embedding similarity over statements to avoid false "entirely new" on minor wording.
   - Stub-first scorer for CI; optional embedding reuse from Phase 3.
3. **APIs**
   - `POST /api/v1/comparisons` (base_version_id, target_version_id)
   - `GET /api/v1/comparisons/{id}` + list changes
   - `PATCH` change decision: confirm / reject
   - Traceability fields on requirements: Jira ID, source file, test case, implementation note
4. **Eval hooks**
   - Confirmed decisions stored for later Phase 7 datasets (mirror `is_eval_example` pattern).
5. **Tests + CI**
   - Synthetic two-version fixtures; alignment unit test for minor paraphrase; compose smoke compare + confirm; contracts regen.
   - ASCII hyphens; no LangChain; no confidential fixtures.

### Non-goals

- Full evaluation harness / CI gates (Phase 7)
- Real multi-tenant auth / RBAC
- Product UI beyond OpenAPI

### Exit criteria to verify before stop

| Criterion | How we will prove it |
| --- | --- |
| Minor wording not reported as entirely new | Alignment unit/integration test |
| Every reported change links old and new source text | Persist + API assert (null allowed only for pure add/remove) |
| Users can confirm or reject detected changes | PATCH + status test |
| Confirmed decisions saved for future evaluations | Flag/store on confirmed rows |

### Implementation sketch

1. Branch `cursor/phase6-version-compare-018c` from Phase 5.
2. Models/migration `20261108_0006`; `app/compare/**` aligner + pipeline; Celery task.
3. Routes under `/api/v1/comparisons`; extend requirement schemas for links.
4. Update CI smoke; regenerate contracts; update progress; open PR; **stop for Phase 7 approval**.

### Risks for Phase 6

- Alignment thresholds will need tuning; stub similarity may under/over-merge.
- Requires both versions to have completed Phase 5 extraction first.
- "Behavior changed" vs "clarified" is subjective without LLM; stub uses heuristics.
