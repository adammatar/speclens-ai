# SpecLens AI - Progress

## Phase 0-5

**Status:** Complete (approved) - PRs #1-#5

---

## Phase 6 - Version comparison and traceability

**Status:** Complete and re-verified (awaiting review / merge; stop before Phase 7)

**Date:** 2026-11-09

**Branch:** `cursor/phase6-version-compare-018c`

**PR:** https://github.com/adammatar/speclens-ai/pull/6

### Architecture and implementation decisions

1. **New versions:** `POST /documents/{id}/versions` uploads a new `DocumentVersion` with incremented `version_number`.
2. **Schema:** Alembic `20261108_0006` adds `comparison_jobs`, `requirement_changes`, and requirement traceability fields (Jira, source file, test case, implementation note).
3. **Alignment:** Match by `external_id` first, then greedy token/sequence similarity (threshold 0.72) so minor wording is not reported as entirely new.
4. **Categories:** added, removed, clarified, behavior_changed, priority_changed, acceptance_criteria_changed, potential_breaking_change, uncertain.
5. **Source linkage:** Non add/remove changes always carry old and new source quotes (fallback to statements).
6. **Review:** Confirm/reject via PATCH; confirmed rows set `is_eval_example` for Phase 7.
7. **Celery:** `speclens.compare_document_versions`; stub-first; no LangChain.

### Acceptance criteria (technical-plan exit criteria)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Minor wording not reported as entirely new | Yes | `test_minor_wording_change_aligns_not_added_removed` |
| Every reported change links old and new source text | Yes | add/remove one-sided OK; others require both quotes (pipeline + smoke) |
| Users can confirm or reject detected changes | Yes | PATCH + tests/smoke |
| Confirmed decisions saved for future evaluations | Yes | `is_eval_example=True` on confirm |

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

### Commands / results (re-verification 2026-11-09)

```text
ruff check app tests              -> pass (exit 0)
mypy app                          -> pass, 62 files (exit 0)
alembic current                   -> 20261108_0006 (head)
python3 -m pytest -q              -> 34 passed, 0 failed (exit 0)
Live compose re-smoke             -> compare succeeded; confirm marks eval
                                     -> REVERIFY6_SMOKE_OK
CI (initial push aec7e71)         -> FAILED: invalid workflow YAML
                                     (multiline python -c broke .github/workflows/ci.yml)
CI fix                            -> collapsed assert to one line; yaml_ok locally
```

**Local test failures:** none.

**CI note:** First Phase 6 push failed immediately (0s, no jobs) due to a YAML parse error in the compose-smoke step. Fix included in this re-verification commit; watching CI on the follow-up push.

### Explicit stop

Phase 7 (evaluation system) is **not started**. Awaiting explicit approval.

### Remaining risks

1. Similarity thresholds may under/over-merge without embedding-based aligner.
2. Clarified vs behavior_changed is heuristic without an LLM judge.
3. Exact-duplicate statement pairs are suppressed from the change list (intentional).
4. Compare requires successful extraction on both versions first.
5. CI must go green after the workflow YAML fix (local verify already green).

---

## Phase 7 plan (proposed) - Evaluation system

**Do not execute until explicitly approved.**

### Goal

Local, version-controlled evaluation harness (`make eval`) with JSONL datasets and JSON/HTML reports covering retrieval, citations, QA, extraction, compare, insufficient-evidence, and prompt-injection resistance. CI can gate on agreed thresholds (start advisory, then blocking).

### Scope (in)

1. **Datasets** under `evals/` (JSONL): retrieval, QA+citations, extraction, compare, insufficient-evidence, injection. Bootstrap with synthetic fixtures; target >=50 questions and >=20 extraction examples.
2. **Graders:** Recall@k, MRR, citation precision/coverage, unsupported-claim rate, extraction F1, compare alignment accuracy, latency/token stubs.
3. **Runner:** `make eval` writes `artifacts/eval/report.json` + HTML summary; baseline comparison for prompt/model changes.
4. **Gold import (optional):** export accepted Phase 5/6 `is_eval_example` rows into eval samples.
5. **CI:** eval job (advisory first if thresholds need calibration; then blocking).
6. Constraints: ASCII hyphens; no LangChain; no confidential fixtures; stub/offline in CI.

### Non-goals

- Hosted tracing product UI
- Real auth (Phase 8)
- Paid OpenAI calls in CI

### Exit criteria to verify before stop

| Criterion | How we will prove it |
| --- | --- |
| `make eval` produces JSON and HTML | Command + artifact paths |
| Prompt/model changes comparable to baseline | Diff section in report |
| CI can block below thresholds | Workflow step (advisory then enforce) |
| >=50 questions and >=20 extraction examples | Dataset counts in report |

### Implementation sketch

1. Branch `cursor/phase7-evaluation-harness-018c` from Phase 6.
2. `evals/` datasets + eval package/tools; Makefile + CI.
3. Update progress; open PR; **stop for Phase 8 approval**.

### Risks for Phase 7

- Synthetic gold labels may inflate metrics vs real specs.
- Threshold calibration needs iteration before hard CI gates.
- Latency/cost metrics are stubs without live model traffic in CI.
