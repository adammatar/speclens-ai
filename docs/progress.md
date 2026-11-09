# SpecLens AI - Progress

## Phase 0-5

**Status:** Complete (approved) - PRs #1-#5

---

## Phase 6 - Version comparison and traceability

**Status:** Complete on branch (awaiting review / merge; stop before Phase 7)

**Date:** 2026-11-09

**Branch:** `cursor/phase6-version-compare-018c`

### Architecture and implementation decisions

1. **New versions:** `POST /documents/{id}/versions` uploads a new `DocumentVersion` with incremented `version_number`.
2. **Schema:** Alembic `20261108_0006` adds `comparison_jobs`, `requirement_changes`, and requirement traceability fields (Jira, source file, test case, implementation note).
3. **Alignment:** Match by `external_id` first, then greedy token/sequence similarity (threshold 0.72) so minor wording is not reported as entirely new.
4. **Categories:** added, removed, clarified, behavior_changed, priority_changed, acceptance_criteria_changed, potential_breaking_change, uncertain.
5. **Source linkage:** Non add/remove changes always carry old and new source quotes (fallback to statements).
6. **Review:** Confirm/reject via PATCH; confirmed rows set `is_eval_example` for Phase 7.
7. **Celery:** `speclens.compare_document_versions`; stub-first; no LangChain.

### Acceptance criteria

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Minor wording not reported as entirely new | Yes | `test_minor_wording_change_aligns_not_added_removed` |
| Every change links old/new source text (add/remove one-sided OK) | Yes | pipeline + live/CI asserts |
| Users can confirm or reject changes | Yes | PATCH + tests/smoke |
| Confirmed decisions saved for eval | Yes | `is_eval_example=True` on confirm |

### Changed files (vs Phase 5)

```text
.github/workflows/ci.yml
README.md
docs/progress.md
packages/contracts/openapi.json
packages/contracts/src/generated.ts
services/api/app/api/routes/comparisons.py
services/api/app/api/routes/documents.py
services/api/app/api/routes/requirements.py
services/api/app/api/schemas.py
services/api/app/compare/__init__.py
services/api/app/compare/align.py
services/api/app/compare/pipeline.py
services/api/app/db/models.py
services/api/app/extraction/service.py
services/api/app/ingestion/__init__.py
services/api/app/ingestion/queue.py
services/api/app/ingestion/service.py
services/api/app/main.py
services/api/migrations/versions/20261108_0006_version_compare.py
services/api/tests/test_compare_align.py
services/api/tests/test_compare_pipeline.py
workers/speclens_worker/tasks.py
```

### Commands / results

```text
ruff check app tests  -> pass
mypy app              -> pass (62 files)
alembic upgrade head  -> 20261108_0006
pytest                -> 34 passed, 0 failed
Live smoke            -> compare succeeded; categories include clarified/behavior_changed/added;
                         confirm marks eval; traceability patch OK
Contracts             -> generated.ts 21 paths
```

**Failures:** none.

### Explicit stop

Phase 7 (evaluation system) not started - awaiting approval.

### Remaining risks

1. Similarity thresholds may under/over-merge without embedding-based aligner.
2. Clarified vs behavior_changed is heuristic without an LLM judge.
3. Exact-duplicate statement pairs are suppressed from the change list (intentional).
4. Compare requires successful extraction on both versions first.

---

## Phase 7 plan (proposed) - Evaluation system

**Do not execute until explicitly approved.**

### Goal

Local, version-controlled evaluation harness (`make eval`) with JSONL datasets and JSON/HTML reports covering retrieval, citations, QA, extraction, compare, insufficient-evidence, and prompt-injection resistance. CI can gate on agreed thresholds (start advisory, then blocking).

### Scope (in)

1. Dataset layout under `evals/` (JSONL): retrieval, QA+citations, extraction, compare, insufficient-evidence, injection.
2. Graders: Recall@k, MRR, citation precision/coverage, unsupported-claim rate, extraction F1, compare alignment accuracy, latency/token stubs.
3. `make eval` runner producing `artifacts/eval/report.json` + HTML summary; baseline comparison for prompt/model changes.
4. Wire accepted Phase 5/6 `is_eval_example` rows into exportable gold samples (optional import).
5. Synthetic fixtures only (>=50 questions and >=20 extraction examples as exit target - may bootstrap with stubs/synthetics).
6. CI job for eval (non-blocking first if thresholds need calibration).

### Non-goals

- Hosted tracing product UI
- Real auth (Phase 8)
- Production OpenAI spend in CI (stub + offline fixtures)

### Exit criteria to verify

| Criterion | Proof |
| --- | --- |
| `make eval` produces JSON and HTML | Command output artifacts |
| Prompt/model changes comparable to baseline | Diff section in report |
| CI can block below thresholds | Workflow step (advisory then enforce) |
| >=50 questions and >=20 extraction examples | Dataset counts in report |

### Implementation sketch

1. Branch `cursor/phase7-evaluation-harness-018c` from Phase 6.
2. `evals/` datasets + `services/api/app/eval/**` or `tools/eval`.
3. Makefile target + CI; update progress; open PR; **stop for Phase 8 approval**.
