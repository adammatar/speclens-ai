# SpecLens AI — Technical Write-up

SpecLens AI is an evaluation-driven platform for reading and governing technical specifications: ingest large docs, retrieve with citations, extract structured requirements, compare versions, and measure quality offline before trusting model changes.

## Problem

Engineering teams drown in long Word/PDF/Markdown specs. Generic chatbots invent citations; spreadsheet extractions drift from source; version diffs are noisy. SpecLens keeps **evidence and eval gates** next to every AI step.

## What shipped (Phases 1–9)

| Layer | Implementation |
| --- | --- |
| API | FastAPI, SQLAlchemy 2, Alembic, structured JSON logs |
| Workers | Celery + Redis (ingest, embed, extract, compare) |
| Data | Postgres 16 + pgvector (FTS + HNSW), filesystem object store |
| Retrieval | Hybrid RRF (vector + lexical) |
| QA | Conversations with allow-listed citations; SSE optional |
| Extraction / compare | Structured requirements + change decisions |
| Security | Hashed API keys, workspace RBAC, rate limits, audit, log redaction |
| Eval | Offline JSONL harness with graders + advisory CI gates |
| Web | React + Vite SPA (`apps/web`) — API key in `sessionStorage` only |

## Architecture

See [`architecture.svg`](./architecture.svg). Browser → FastAPI → Postgres/Redis/object storage; workers share the data plane. Optional OpenAI for embeddings/generation/extraction; local/CI defaults to stubs.

## Evaluation (offline)

Latest harness run (stub backends; synthetic gold):

| Metric | Value | Gate |
| --- | --- | --- |
| Retrieval Recall@10 | 1.00 | pass |
| Retrieval MRR | 0.96 | pass |
| Citation precision | 1.00 | pass |
| Citation coverage | 0.98 | pass |
| Unsupported claim rate | 0.00 | pass |
| Extraction F1 | 0.94 | pass |
| Compare alignment | 1.00 | pass |
| Insufficient-evidence accuracy | 0.92 | pass |
| Injection resistance | 1.00 | pass |

Dataset counts: retrieval 40 + QA 20 = 60 question-like examples; extraction 24; plus compare / IE / injection suites. Reports: `make eval` → `artifacts/eval/report.{json,html}`.

**Caveat:** Stub backends + synthetic fixtures inflate absolute scores vs production LLM traffic. The harness’s job is **regression control**, not marketing accuracy claims.

## Performance notes

- Local Compose smoke (stub backends): Markdown upload → ingest → search → cited QA → extract → compare completes in well under a minute on a single developer machine.
- Upload cap default 50 MiB; chunking preserves heading paths / offsets for provenance.
- Rate limit default 120 req/min per sensitive bucket (in-process; not Redis-shared yet).

## Security summary

- API keys hashed at rest; bootstrap local key documented for DX only — rotate before hosted use.
- Cross-workspace access fail-closed; `/health`, `/ready`, `/meta` public.
- Logs redact secrets and document bodies.
- Complete delete removes DB rows and object bytes.
- Details: [`docs/security.md`](../security.md).

## Individual contribution

This repository was implemented as a phased greenfield build (engineering foundation → ingestion → retrieval → cited QA → extraction → compare → eval harness → security → React UX/deploy → portfolio packaging), with stop-for-approval between phases and CI on each stacked PR.

## Portfolio case study (one-pager)

**Situation.** Spec review is slow and AI helpers often invent citations or lose provenance.

**Approach.** One API (FastAPI) with hybrid retrieval, cited QA, structured extraction, version compare, offline eval gates, API-key RBAC, and a React operator UI — stubs by default so CI stays free of live LLM spend.

**Result.** End-to-end local/prod-style Compose path; eval harness with ≥50 questions and ≥20 extraction examples; portfolio media regenerated deterministically without browser password-manager UI.

**Résumé line.** Built an evaluation-driven AI platform for technical specifications using Python, FastAPI, PostgreSQL/pgvector and optional LLM APIs — hybrid retrieval, cited answers, structured requirement extraction, document versioning, and automated evaluation of retrieval quality and citation accuracy.

## Demo without confidential data

Use synthetic fixtures only (`services/api/tests/fixtures/sample.md`, eval JSONL). Reset locally with `./scripts/demo_reset.sh`. Do not publish customer SharePoint/DOCX content.
