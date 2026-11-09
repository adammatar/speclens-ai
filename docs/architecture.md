# SpecLens AI - Architecture

Adapts the technical plan monorepo. Existing Local Docs Viewer justifies UX and parsing *ideas*, not keeping Electron/Node as the platform spine.

## Target shape

```
speclens-ai/                          # GitHub repository
├── apps/
│   └── web/                          # React + Vite SPA (Phase 9)
├── services/
│   └── api/                          # FastAPI (SQLAlchemy 2, Alembic, Pydantic settings)
├── workers/                          # Redis-backed Celery workers
├── evals/                            # Versioned datasets, graders, reports
├── prompts/                          # Answering / extraction / comparison prompt versions
├── packages/
│   └── contracts/                    # OpenAPI -> TypeScript types
├── infra/
│   ├── docker/
│   └── compose.yaml                  # api, worker, postgres(pgvector), redis
├── docs/
│   ├── architecture.md
│   ├── security.md
│   ├── evaluation.md
│   ├── progress.md
│   └── decisions/
├── .env.example
├── Makefile
└── README.md
```

## Runtime diagram

```
React + Vite web (and optional future Electron shell)
          |
          v
     FastAPI API  ---- OpenAI Responses + Embeddings
          |
    +-----+------+
    v            v
Postgres      Redis queue
pgvector      |
    |         v
Object store  Workers (ingest, embed, extract, eval)
```

## Local mode vs hosted mode

**Hosted mode (default portfolio/prod path):**

- Users/workspaces, upload DOCX/PDF/Markdown to object storage
- Server-side parse, embed, answer; API keys never in browser
- Multi-tenant isolation enforced in API queries

**Local mode (preserve Local Docs Viewer privacy story):**

- Single-user or air-gapped compose stack on laptop
- Documents stay on local disk / local MinIO
- Same FastAPI contracts; config flags disable outbound telemetry
- Electron wrapper is optional Phase 9+ packaging, not Phase 1 foundation

Do not fork two codebases. One API with deployment profiles.

## Supported files

MVP ingest (Phase 2+): **DOCX**, **text-based PDF**, **Markdown**. Reject encrypted/scanned-only PDFs with clear errors until OCR is scoped later.

## Non-goals for early phases

- LangChain (or equivalent heavy agent frameworks) for MVP
- Chatbot-only wrapper without eval harness
- Shipping Electron in Phase 1
- Committing real customer/SharePoint DOCX fixtures
- Multi-region HA

## Phase 1 foundation

Compose-backed FastAPI + Postgres/pgvector + Redis + Celery worker skeleton, health/ready, migrations, logging, contracts stub, lint/test/CI - empty of product AI features beyond scaffolding.

See `progress.md` for acceptance criteria and status.
