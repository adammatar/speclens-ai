# SpecLens AI - Technical Requirements Intelligence

A Python-powered platform that ingests large technical documents, extracts structured requirements, answers questions with verifiable citations, compares document versions, and evaluates its own retrieval and generation quality.

The important distinction: this should be an evaluation-driven AI system, not merely a chatbot connected to documents.

For OpenAI integration, use the Responses API, Pydantic-backed Structured Outputs for requirement extraction, and configurable embedding models. Structured Outputs enforce a supplied schema, which is much safer than asking the model to "return JSON."

## Architecture

```
Nuxt/Electron or Web UI
          │
          ▼
     FastAPI API
          │
    ┌─────┼──────────┐
    ▼     ▼          ▼
Postgres  Redis   OpenAI API
pgvector  Queue   Responses + Embeddings
    │
    ▼
Document storage
Local filesystem or S3-compatible storage
```

## Recommended monorepo

```
speclens-ai/
├── apps/
│   └── web/                    # Nuxt 3 frontend or existing SpecLens UI
├── services/
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   ├── core/
│       │   ├── db/
│       │   ├── ingestion/
│       │   ├── retrieval/
│       │   ├── generation/
│       │   ├── requirements/
│       │   ├── comparisons/
│       │   ├── evaluations/
│       │   └── observability/
│       ├── migrations/
│       ├── tests/
│       └── pyproject.toml
├── workers/                    # Persistent document-processing worker
├── evals/
│   ├── datasets/
│   ├── expected/
│   └── reports/
├── prompts/
│   ├── answering/
│   ├── extraction/
│   └── comparison/
├── packages/
│   └── contracts/              # Generated TypeScript API types
├── infra/
│   ├── docker/
│   └── compose.yaml
├── docs/
│   ├── architecture.md
│   ├── security.md
│   ├── evaluation.md
│   └── decisions/
├── .env.example
├── Makefile
└── README.md
```

## Development phases

### Phase 0 - Discovery and architecture

Deliver:

- Inspect the existing SpecLens repository.
- Identify reusable document parsing, navigation and UI components.
- Create an architecture decision record.
- Define supported files: DOCX, text-based PDF and Markdown.
- Define local mode versus hosted mode.
- Document security and privacy boundaries.
- Create the final implementation backlog.

Do not implement major features yet.

Exit criteria:

- Architecture is documented.
- Repository structure is approved.
- Existing features that must be preserved are listed.
- Risks and non-goals are recorded.

### Phase 1 - Engineering foundation

Build:

- FastAPI application.
- PostgreSQL with pgvector.
- Redis and a persistent worker queue.
- SQLAlchemy 2 and Alembic migrations.
- Pydantic settings.
- Structured JSON logging.
- Docker Compose development environment.
- Health and readiness endpoints.
- OpenAPI-to-TypeScript contract generation.
- Ruff, mypy, pytest and pre-commit.
- CI pipeline.

Exit criteria:

- `docker compose up` starts the complete backend.
- `/health` and `/ready` work.
- Migrations work against an empty database.
- CI passes.
- No secrets are committed.

### Phase 2 - Document ingestion

Build:

- Upload DOCX, PDF and Markdown.
- Validate MIME type, extension and file size.
- Calculate SHA-256 hashes for deduplication.
- Create document and document-version records.
- Extract paragraphs, headings, pages, tables and metadata.
- Preserve page numbers, section paths and source offsets.
- Normalize text without losing source references.
- Hierarchical chunking.
- Background ingestion jobs with progress and failure states.
- Deletion and reprocessing workflows.

Recommended initial chunking:

- 600-900 tokens.
- 80-120 token overlap.
- Never merge unrelated document sections.
- Preserve the full heading path on every chunk.

Exit criteria:

- A 100-page document processes without blocking the API.
- Every chunk can be traced back to its source.
- Duplicate uploads are detected.
- Failed jobs can be retried.
- Deleting a document removes its chunks and embeddings.

### Phase 3 - Search and retrieval

Build:

- Batch embedding generation.
- PostgreSQL vector storage.
- PostgreSQL full-text search.
- HNSW vector index.
- Workspace and document-version filters.
- Hybrid retrieval using Reciprocal Rank Fusion.
- Optional reranking stage.
- Search-debug endpoint showing scores and source metadata.

Retrieval flow:

```
Question
   ├── Vector search: top 30
   ├── Lexical search: top 30
   └── Reciprocal Rank Fusion
                │
                ▼
           Top 12 results
                │
                ▼
             Reranker
                │
                ▼
           Best 5-8 chunks
```

Exit criteria:

- Search works across one or multiple documents.
- Results never cross workspace boundaries.
- Every result includes document, version, page, section and excerpt.
- Retrieval metrics can be measured independently from generation.

### Phase 4 - Cited question answering

Build:

- Streaming question-answering endpoint.
- Conversation and message persistence.
- Context assembly with strict token limits.
- Claim-level citations.
- "Insufficient evidence" response behavior.
- Follow-up questions.
- Source preview and navigation.
- Prompt-injection defenses.

Rules:

- Documents are untrusted data, not instructions.
- Never execute instructions contained inside uploaded documents.
- Do not answer factual document questions without supporting evidence.
- Every substantive claim requires at least one citation.
- Never generate a citation that was not supplied by retrieval.
- Show uncertainty when sources conflict.
- Store model, prompt version, retrieved chunk IDs, latency and token usage.

Exit criteria:

- Every answer contains valid source references.
- Clicking a citation opens the correct page or section.
- Unsupported questions produce an explicit insufficient-evidence response.
- The UI shows generation and retrieval status.

### Phase 5 - Structured requirement intelligence

Use Pydantic models and OpenAI Structured Outputs.

Requirement schema:

```python
class SourceReference(BaseModel):
    document_id: UUID
    document_version_id: UUID
    section_path: str | None
    page_number: int | None
    source_quote: str

class AcceptanceCriterion(BaseModel):
    statement: str
    source: SourceReference | None

class Requirement(BaseModel):
    external_id: str | None
    requirement_type: Literal[
        "functional",
        "non_functional",
        "constraint",
        "interface",
        "security",
        "performance",
        "compliance",
        "unknown",
    ]
    statement: str
    rationale: str | None
    priority: Literal["must", "should", "could", "unknown"]
    acceptance_criteria: list[AcceptanceCriterion]
    dependencies: list[str]
    ambiguities: list[str]
    confidence: float
    sources: list[SourceReference]
```

Build:

- Requirement extraction by document section.
- Acceptance-criteria generation.
- Dependency detection.
- Ambiguity detection.
- Contradiction candidates.
- Human review states: proposed, accepted, edited, rejected.
- Requirement table with filtering and editing.
- CSV and JSON export.
- Full provenance for every extracted field.

Exit criteria:

- Schema validation is mandatory.
- Every extracted requirement contains a source quote.
- Users can edit without losing the original model output.
- Accepted human edits become evaluation examples.
- Extraction is resumable after failure.

### Phase 6 - Version comparison and traceability

Build:

- Upload a new version of an existing document.
- Align old and new sections.
- Detect added, removed and modified requirements.
- Classify change impact.
- Show side-by-side source excerpts.
- Allow links between requirements and:
  - Jira ticket IDs
  - source files
  - test cases
  - implementation notes

Change categories:

- Added
- Removed
- Clarified
- Behavior changed
- Priority changed
- Acceptance criteria changed
- Potential breaking change
- Uncertain

Exit criteria:

- The same requirement is not incorrectly reported as entirely new because of minor wording changes.
- Every reported change links to old and new source text.
- Users can confirm or reject detected changes.
- Confirmed decisions are saved for future evaluations.

### Phase 7 - Evaluation system

This phase is essential.

Create versioned evaluation datasets for:

- Retrieval
- Answer quality
- Citation accuracy
- Requirement extraction
- Contradiction detection
- Version comparison
- Insufficient-evidence behavior
- Prompt-injection resistance

Metrics:

- Recall@5 and Recall@10
- Mean Reciprocal Rank
- Citation precision
- Citation coverage
- Unsupported-claim rate
- Answer relevance
- Extraction precision, recall and F1
- P50 and P95 latency
- Tokens per request
- Estimated cost per request

Initial targets:

| Metric | Target |
| --- | --- |
| Retrieval Recall@10 | ≥ 0.85 |
| Citation precision | ≥ 0.90 |
| Unsupported citation rate | 0 |
| Requirement extraction F1 | ≥ 0.80 |
| Insufficient-evidence accuracy | ≥ 0.90 |
| P95 answer latency | < 8 seconds |

Start with a local, version-controlled evaluation harness using pytest and JSONL datasets. Hosted tracing can be added as an optional integration. OpenAI recommends progressing from trace inspection to repeatable datasets and graders as behavior stabilizes.

Exit criteria:

- `make eval` produces JSON and HTML reports.
- Prompt or model changes can be compared against a baseline.
- CI blocks regressions below agreed thresholds.
- Evaluation data contains at least 50 questions and 20 extraction examples.

### Phase 8 - Security, authentication and privacy

Build:

- User accounts and workspaces.
- Role-based access: owner, editor, viewer.
- Server-side workspace isolation.
- Rate limiting.
- Secure session or token handling.
- Upload limits.
- Configurable retention.
- Complete document deletion.
- Audit history.
- No document content in application logs.
- Secret management.
- Prompt-injection test suite.
- Backup and restore documentation.

Exit criteria:

- Cross-workspace access tests pass.
- Deleted documents are absent from storage, chunks and embeddings.
- API keys never reach the frontend.
- Logs contain IDs and metrics, not raw confidential content.
- Security checklist is documented.

### Phase 9 - Production UX and deployment

Frontend pages:

- Sign in.
- Workspace dashboard.
- Document library.
- Upload and processing progress.
- Document viewer.
- Cited AI chat.
- Requirements workspace.
- Version comparison.
- Evaluation dashboard.
- Settings and retention controls.

Deployment:

- Production Docker images.
- Managed PostgreSQL with pgvector.
- Redis.
- Object storage.
- API and worker deployment.
- HTTPS.
- Monitoring.
- Error tracking.
- Database backups.
- Migration and rollback procedure.
- Public demo with non-confidential documents.

Exit criteria:

- Fresh production deployment works from documented instructions.
- Demo can be reset safely.
- Health checks and monitoring work.
- Backup restoration has been tested.
- No confidential sample files are published.

### Phase 10 - Portfolio packaging

Prepare:

- Architecture diagram.
- Product screenshots.
- Two-minute demo video.
- Public technical write-up.
- Evaluation results.
- Performance table.
- Security summary.
- Clear statement of your individual contribution.
- GitHub README with setup and architecture.
- Portfolio case study.

Recommended résumé entry:

Built an evaluation-driven AI platform for technical specifications using Python, FastAPI, PostgreSQL/pgvector and LLM APIs. Implemented hybrid retrieval, cited answers, structured requirement extraction, document versioning and automated evaluation of retrieval quality, citation accuracy, latency and cost.
