# ADR 0001 - Target Architecture and Repository Strategy

- Status: Accepted
- Date: 2026-11-08
- Context: SpecLens AI technical plan + inspection of local Local Docs Viewer

## Context

Two plausible paths:

1. **Evolve** the local Local Docs Viewer folder into SpecLens AI (add Python services beside Nuxt/Electron).
2. **Greenfield** a new GitHub repo (`speclens-ai`) with FastAPI + Postgres/pgvector + Redis + Nuxt, optionally borrowing UI/parsing ideas from the local app.

The local app is a private offline DOCX viewer: Nuxt SPA + Electron, mammoth/cheerio sectioning, substring search, userData JSON cache. No tests, no remotes, no AI, no Postgres.

The product plan requires an evaluation-driven AI system (not a chatbot wrapper), Python FastAPI, pgvector, Redis workers, OpenAI Responses API, and no LangChain for MVP.

## Decision

**Create a new GitHub repository and start greenfield on the Python backend monorepo.** Treat the Local Docs Viewer as a design and parsing reference, not as the application root.

Optionally later:

- Port viewer UX into `apps/web`
- Revisit Electron as a thin shell for local mode (after API exists)
- Keep the local folder as a historical prototype (do not rewrite it in place)

## Consequences

### Positive

- Clean history and portfolio narrative
- Stack matches eval/ingestion/retrieval work from day one
- Avoids Electron packaging and Node DOCX pipeline constraining server design
- Clear separation: prototype vs product

### Negative / costs

- Cannot `git mv` continuity from the prototype
- Must re-implement document viewing in the new Nuxt app
- Temporary dual folders on disk until prototype is archived or linked from README

### Rejected alternative

Evolving the Nuxt/Electron app as the monorepo root was rejected because the durable system is the Python evaluation-driven platform; the desktop viewer is a small UX prototype with mismatched persistence and search.

## Related

- `docs/architecture.md`
- `docs/security.md`
- `docs/technical-plan.md`
