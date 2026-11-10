# SpecLens AI — Technical Write-up

SpecLens AI is an evaluation-driven platform for reading and governing technical specifications: ingest large docs, retrieve with citations, extract structured requirements, compare versions, and measure quality with a **runtime** evaluation harness before trusting model changes.

## Problem

Engineering teams drown in long Word/PDF/Markdown specs. Generic chatbots invent citations; spreadsheet extractions drift from source; version diffs are noisy. SpecLens keeps **evidence and eval gates** next to every AI step.

## What shipped

| Layer | Implementation |
| --- | --- |
| API | FastAPI, SQLAlchemy 2, Alembic, structured JSON logs |
| Workers | Celery + Redis (ingest, embed, extract, compare, retention) |
| Data | Postgres 16 + pgvector (FTS + HNSW), filesystem object store |
| Retrieval | Hybrid RRF (vector + lexical) |
| QA | Conversations with allow-listed citations; fail-closed when unsupported |
| Extraction / compare | Structured requirements + change decisions |
| Security | Hashed API keys, workspace RBAC, Redis rate limits, audit, log redaction, hosted startup guards |
| Eval | Runtime stub/live harness; CI enforces stub thresholds |
| Web | React + Vite SPA — Home, Documents, Requirements, Compare, Evaluation, Settings (EN/HE RTL) |

## Architecture

See [`architecture.svg`](./architecture.svg). Browser → FastAPI → Postgres/Redis/object storage; workers share the data plane. Optional OpenAI/Gemini-compatible backends; local/CI defaults to stubs.

## Evaluation methodology

1. Gold JSONL contains **inputs and labels only** (no `predicted_*`).
2. At runtime the harness ingests `evals/corpus/*`, embeds, retrieves, runs QA/extract/compare.
3. Predictions are graded against gold; reports record mode, backends, commit, latencies.
4. `make eval EVAL_ENFORCE=1` fails on threshold regressions.

Latest **stub / synthetic** run (deterministic backends on fixtures):

| Metric | Value | Gate |
| --- | --- | --- |
| Retrieval Recall@5 / @10 | 1.00 / 1.00 | pass |
| Retrieval MRR | 1.00 | pass |
| Citation precision / coverage | 1.00 / 1.00 | pass |
| Unsupported claim rate | 0.00 | pass |
| Extraction P/R/F1 | 1.00 | pass |
| Compare alignment | 1.00 | pass |
| Insufficient-evidence accuracy | 1.00 | pass |
| Injection resistance | 1.00 | pass |

**Caveat:** These scores measure stub/synthetic pipeline behavior. They are **not** measured production accuracy for live LLM providers.

## Security summary

- API keys hashed at rest; local bootstrap activated only via `bootstrap-local` (never in production Compose).
- Hosted startup refuses weak DB passwords, `AUTH_REQUIRED=false`, and an active public bootstrap key.
- Redis-backed rate limits in hosted mode; correlation IDs + optional redacted Sentry.
- Retention sweeps are functional and gated; deployment-wide `RETENTION_DAYS`.
- Details: [`docs/security.md`](../security.md) · [`docs/deploy.md`](../deploy.md).

## Individual contribution

Phased greenfield build (foundation → ingest → retrieval → cited QA → extraction → compare → eval → security → React UX → production hardening), with CI on stacked PRs and synthetic-only public fixtures.

## Portfolio case study (one-pager)

**Situation.** Spec review is slow and AI helpers often invent citations or lose provenance.

**Approach.** One API (FastAPI) with hybrid retrieval, cited QA, structured extraction, version compare, runtime eval gates, API-key RBAC, and a React operator UI — stubs by default so CI stays free of live LLM spend.

**Result.** End-to-end local + production-style Compose path; runtime eval harness; Requirements/Compare/Evaluation product surfaces; portfolio media without confidential content.

**Résumé line.** Built an evaluation-driven AI platform for technical specifications using Python, FastAPI, PostgreSQL/pgvector and optional LLM APIs — hybrid retrieval, fail-closed cited answers, structured requirement extraction, document versioning, bilingual UI, and automated runtime evaluation of retrieval quality and citation accuracy.

## Demo without confidential data

Use synthetic fixtures only (`demos/`, `evals/corpus/`, `services/api/tests/fixtures/sample.md`). Reset locally with `./scripts/demo_reset.sh`. Do not publish customer SharePoint/DOCX content.
