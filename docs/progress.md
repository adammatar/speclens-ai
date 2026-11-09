# SpecLens AI - Progress

## Phase 0-4

**Status:** Complete (approved) - PRs #1-#4

---

## Phase 5 - Structured requirement intelligence

**Status:** Complete on branch (awaiting review / merge; stop before Phase 6)

**Date:** 2026-11-09

**Branch:** `cursor/phase5-requirement-extraction-018c`

### Architecture and implementation decisions

1. **Schema:** Pydantic `SourceReference` / `AcceptanceCriterion` / `RequirementDraft` with mandatory non-empty `source_quote`; re-validated on persist and edit.
2. **Persistence:** Alembic `20261108_0005` adds `extraction_jobs` (section cursor, progress) and `requirements` (review state, immutable `original_payload`, `is_eval_example`).
3. **Extraction:** Section-grouped chunks; stub heuristic modal extractor default; optional OpenAI Structured Outputs via urllib Responses API.
4. **Resumability:** Jobs advance `section_cursor` per section; failures persist cursor; re-run continues from cursor.
5. **Review:** States `proposed` / `edited` / `accepted` / `rejected`; edits never mutate `original_payload`; `accepted` sets `is_eval_example`.
6. **APIs:** start extraction, job status, list/filter, patch, CSV/JSON export. Celery task `speclens.extract_requirements`.
7. **Safety:** No LangChain; prompts treat docs as data; logs omit raw document bodies; synthetic fixtures only.

### Acceptance criteria

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Schema validation mandatory | Yes | `RequirementDraft` + persist/edit re-validate; schema tests |
| Every extracted requirement has source quote | Yes | Stub + schema; pipeline/CI asserts |
| Edit without losing original model output | Yes | `original_payload` immutable; pipeline test |
| Accepted human edits become eval examples | Yes | `is_eval_example=True` on accept |
| Extraction resumable after failure | Yes | `fail_after_sections` + resume test |
| List/filter + CSV/JSON export | Yes | API + export test + compose smoke |

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

### Commands / results

```text
ruff check app tests     -> pass
mypy app                 -> pass (58 files)
alembic upgrade head     -> 20261108_0005
pytest                   -> 29 passed, 0 failed
Live compose smoke       -> extract succeeded; 5 requirements with quotes;
                           edit+accept preserves original_payload; JSON export OK
Contracts                -> generated.ts 17 paths
```

**Failures:** none.

### Explicit stop

Phase 6 (version comparison / traceability) not started - awaiting approval.

### Remaining risks

1. Stub extraction is heuristic (shall/must/should); OpenAI path optional and untested in CI without keys.
2. Contradiction candidates are schema-ready but stub rarely fills them.
3. Section boundaries follow `heading_path` groups from Phase 2 chunking quality.
4. No product UI table yet (API + OpenAPI only).

---

## Phase 6 plan (proposed) - Version comparison and traceability

**Do not execute until explicitly approved.**

### Goal

Compare two document versions' extracted requirements: align sections, detect added/removed/modified requirements with change categories, side-by-side sources, human confirm/reject, and optional links to Jira/tests/files/notes.

### Scope (in)

1. Version upload already exists; add explicit "compare version A vs B" job/API.
2. Requirement alignment (embedding/text similarity + external_id when present) to avoid false "new" on minor wording.
3. Change categories: added, removed, clarified, behavior changed, priority changed, acceptance criteria changed, potential breaking, uncertain.
4. Persist comparison results with old/new source quotes; confirm/reject decisions for future eval.
5. Traceability link fields on requirements (Jira, source file, test case, implementation note).
6. Stub-first alignment; synthetic fixtures; tests + compose smoke; contracts update.

### Non-goals

- Full eval harness / CI gates (Phase 7)
- Real multi-tenant auth
- Product UI beyond API contracts

### Exit criteria to verify

| Criterion | Proof |
| --- | --- |
| Minor wording not reported as entirely new | Alignment unit/integration test |
| Every change links old and new source text | Persist + API assert |
| Users confirm/reject detected changes | PATCH + status test |
| Confirmed decisions saved for eval | Flag/store like Phase 5 eval examples |
