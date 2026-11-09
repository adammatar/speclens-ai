# SpecLens AI - Progress

## Phase 0-6

**Status:** Complete (approved) - PRs #1-#6

---

## Phase 7 - Evaluation system

**Status:** Complete on branch (awaiting review / merge; stop before Phase 8)

**Date:** 2026-11-09

**Branch:** `cursor/phase7-evaluation-harness-018c`

### Architecture and implementation decisions

1. Offline harness under `evals/harness` (`python -m evals.harness` / `make eval`) - no live LLM spend in CI.
2. Versioned JSONL suites: retrieval, QA citations, extraction, compare, insufficient-evidence, injection (synthetic fixtures).
3. Graders: Recall@10, MRR, citation precision/coverage, unsupported-claim rate, extraction F1, compare alignment, IE accuracy, injection resistance.
4. Reports: `artifacts/eval/report.json` + `.html`; copies under `evals/reports/latest.*` (gitignored).
5. Baseline diff vs `evals/baselines/baseline_v1.json` for prompt/model change comparison.
6. Thresholds in `evals/thresholds.json`; CI job advisory unless `EVAL_ENFORCE=true`.
7. Optional `scripts/export_eval_examples.py` imports Phase 5/6 `is_eval_example` rows.

### Acceptance criteria

| Criterion | Met? | Evidence |
| --- | --- | --- |
| `make eval` produces JSON and HTML | Yes | local run + runner smoke test |
| Prompt/model changes comparable to baseline | Yes | `baseline_diff` section in report |
| CI can block below thresholds | Yes | `EVAL_ENFORCE` / `--enforce`; advisory by default |
| >=50 questions and >=20 extraction examples | Yes | 60 question-like rows; 24 extraction rows |

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
evals/datasets/*.jsonl
evals/harness/**
evals/tests/**
evals/thresholds.json
pyproject.toml
scripts/export_eval_examples.py
scripts/generate_eval_datasets.py
```

### Commands / results

```text
make eval                         -> all gates passed; report.json + report.html
ruff check/format (api/workers/evals/scripts) -> pass
pytest                            -> 40 passed, 0 failed
dataset counts                    -> retrieval 40 + qa 20 = 60 questions; extraction 24
```

**Failures:** none.

### Explicit stop

Phase 8 (security, authentication, privacy) not started - awaiting approval.

### Remaining risks

1. Synthetic gold/predictions can inflate offline metrics vs production traffic.
2. Advisory CI gates need calibration before hard enforcement.
3. Latency/cost are not yet first-class measured channels (stubs reserved).
4. Live-system prediction capture (API → predictions JSONL) is future work.

---

## Phase 8 plan (proposed) - Security, authentication and privacy

**Do not execute until explicitly approved.**

### Goal

Add workspace-aware authn/authz, harden upload/secret handling, and document privacy boundaries without breaking local stub workflows.

### Scope (in)

1. Auth model: API keys or OIDC-lite for local; workspace membership on documents/conversations/requirements.
2. Enforce workspace scoping on all read/write routes (fail closed).
3. Upload limits, MIME allow-list audit, virus-scan hook stub, rate limits on QA/extract/compare.
4. Secrets: no keys in logs; redact prompts; `.env.example` only.
5. Privacy docs: retention, deletion (already have document delete), audit log table for sensitive actions.
6. Tests for unauthorized cross-workspace access; CI smoke with auth header.

### Non-goals

- Full enterprise SSO/SCIM
- Customer-managed keys / VPC peering
- Public multi-tenant marketing site

### Exit criteria to verify

| Criterion | Proof |
| --- | --- |
| Unauthenticated sensitive routes rejected | API tests |
| Cross-workspace access denied | Integration tests |
| Secrets never logged | Log redaction unit test |
| Local stub mode still works without SSO | Compose smoke |

### Implementation sketch

1. Branch `cursor/phase8-security-auth-018c` from Phase 7.
2. Migration for users/api_keys/memberships/audit_events.
3. Auth middleware + workspace filters; update OpenAPI security schemes.
4. Progress + PR; **stop for Phase 9 (if any) / release hardening approval**.
