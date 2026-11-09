# SpecLens AI - Progress

## Phase 0-6

**Status:** Complete (approved) - PRs #1-#6

---

## Phase 7 - Evaluation system

**Status:** Complete and re-verified (awaiting review / merge; stop before Phase 8)

**Date:** 2026-11-09

**Branch:** `cursor/phase7-evaluation-harness-018c`

**PR:** https://github.com/adammatar/speclens-ai/pull/7

### Architecture and implementation decisions

1. Offline harness under `evals/harness` (`python -m evals.harness` / `make eval`) - no live LLM spend in CI.
2. Versioned JSONL suites: retrieval, QA citations, extraction, compare, insufficient-evidence, injection (synthetic fixtures).
3. Graders: Recall@10, MRR, citation precision/coverage, unsupported-claim rate, extraction F1, compare alignment, IE accuracy, injection resistance.
4. Reports: `artifacts/eval/report.json` + `.html`; copies under `evals/reports/latest.*` (gitignored).
5. Baseline diff vs `evals/baselines/baseline_v1.json` for prompt/model change comparison.
6. Thresholds in `evals/thresholds.json`; CI job advisory unless `EVAL_ENFORCE=true` / `--enforce`.
7. Optional `scripts/export_eval_examples.py` imports Phase 5/6 `is_eval_example` rows.

### Acceptance criteria (technical-plan exit criteria)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| `make eval` produces JSON and HTML | Yes | re-run wrote both artifacts; runner smoke test |
| Prompt/model changes comparable to baseline | Yes | non-empty `baseline_diff` in report |
| CI can block below thresholds | Yes | `--enforce` / `EVAL_ENFORCE`; advisory by default |
| >=50 questions and >=20 extraction examples | Yes | 60 question-like; 24 extraction |

### Changed files (vs Phase 6)

```text
.github/workflows/ci.yml
.gitignore
Makefile
README.md
docs/evaluation.md
docs/progress.md
evals/__init__.py
evals/baselines/baseline_v1.json
evals/datasets/compare_v1.jsonl
evals/datasets/extraction_v1.jsonl
evals/datasets/injection_v1.jsonl
evals/datasets/insufficient_evidence_v1.jsonl
evals/datasets/qa_citations_v1.jsonl
evals/datasets/retrieval_v1.jsonl
evals/harness/__init__.py
evals/harness/__main__.py
evals/harness/graders.py
evals/harness/metrics.py
evals/harness/report.py
evals/harness/runner.py
evals/tests/test_metrics.py
evals/tests/test_runner_smoke.py
evals/thresholds.json
pyproject.toml
scripts/export_eval_examples.py
scripts/generate_eval_datasets.py
```

### Commands / results (re-verification 2026-11-09)

```text
ruff check services/api workers evals scripts     -> pass
ruff format --check ...                           -> pass (104 files)
python3 -m pytest -q                              -> 40 passed, 0 failed
make eval                                         -> all gates passed; report.json + report.html
python -m evals.harness --enforce                 -> exit 0 (gates pass)
CI (PR #7): Lint/pytest SUCCESS; Evaluation harness SUCCESS; Compose smoke SUCCESS
Dataset counts: retrieval 40 + qa 20 = 60 questions; extraction 24
```

**Failures:** none.

### Explicit stop

Phase 8 (security, authentication, privacy) is **not started**. Awaiting explicit approval.

### Remaining risks

1. Synthetic gold/predictions can inflate offline metrics vs production traffic.
2. Advisory CI gates need calibration before hard enforcement.
3. Latency/cost are not yet first-class measured channels.
4. Live-system prediction capture (API → predictions JSONL) is future work.

---

## Phase 8 plan (proposed) - Security, authentication and privacy

**Do not execute until explicitly approved.**

### Goal

Workspace-aware authentication and authorization, hardened uploads/secrets/logging, audit history, and documented privacy/retention controls - without breaking local stub Compose workflows.

### Scope (in)

1. **Identity & workspaces**
   - Users + API tokens (local-friendly); optional OIDC later.
   - Roles: owner / editor / viewer on a workspace.
2. **Authorization**
   - Server-side workspace isolation on documents, conversations, requirements, comparisons, search.
   - Fail closed for missing/invalid credentials on sensitive routes; keep `/health` public.
3. **Hardening**
   - Rate limits on upload/QA/extract/compare.
   - Upload size/MIME allow-list audit; retention config; complete deletion already present - verify storage+chunks+embeddings gone under auth.
4. **Privacy & secrets**
   - No document bodies or API keys in logs; redaction helpers + tests.
   - Secret management docs; `.env.example` only.
5. **Audit**
   - `audit_events` table for upload/delete/export/accept decisions.
6. **Tests + CI**
   - Cross-workspace denial tests; auth header compose smoke; prompt-injection suite already in evals - keep green.
   - Update OpenAPI security schemes + contracts.

### Non-goals

- Full enterprise SSO/SCIM / customer-managed KMS
- Public multi-tenant marketing site
- Phase 9 production UX frontend

### Exit criteria to verify before stop

| Criterion | How we will prove it |
| --- | --- |
| Cross-workspace access denied | Integration tests |
| Deleted docs absent from storage/chunks/embeddings | Delete test under auth |
| API keys never reach the frontend | Contracts/docs + no key in web bundle |
| Logs hold IDs/metrics, not confidential content | Redaction unit tests |
| Security checklist documented | `docs/security.md` update |

### Implementation sketch

1. Branch `cursor/phase8-security-auth-018c` from Phase 7.
2. Migration `20261108_0008` (users, memberships, api_keys, audit_events).
3. Auth dependency + workspace filters on routes; rate limit middleware.
4. Tests + CI; progress; PR; **stop for Phase 9 approval**.

### Risks for Phase 8

- Local DX friction if auth is too strict without a clear stub token path.
- Migrating existing default-workspace data needs a bootstrap owner.
- Rate limits must not flake CI smoke.
