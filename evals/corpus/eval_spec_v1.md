# SpecLens Synthetic Eval Spec v1

Synthetic fixture for evaluation only. No confidential content.

## Authentication

### Multi-factor authentication

[[GOLD:auth-mfa]] The system shall require multi-factor authentication for all administrative users before granting console access.

### Session timeout

[[GOLD:auth-timeout]] The system shall expire inactive sessions after thirty minutes.

### Password policy

[[GOLD:auth-password]] The system shall reject passwords shorter than twelve characters.

## Document ingestion

### Markdown uploads

[[GOLD:ingest-markdown]] The system shall accept Markdown uploads and preserve heading paths on every chunk.

### Unsupported types

[[GOLD:ingest-reject]] The system shall reject unsupported file types with a clear validation error.

### Duplicate detection

[[GOLD:ingest-dedupe]] The system shall detect duplicate uploads using a SHA-256 content digest.

### Background workers

[[GOLD:ingest-async]] Processing shall not block the API request thread; ingestion runs in a background worker.

## Search and retrieval

### Hybrid search

[[GOLD:search-hybrid]] The system shall retrieve chunks using hybrid lexical and vector search fused with reciprocal rank fusion.

### Workspace isolation

[[GOLD:search-workspace]] The system shall never return chunks from another workspace.

### Result limit

[[GOLD:search-limit]] The system shall return at most twelve search hits for a standard query.

## Cited question answering

### Evidence required

[[GOLD:qa-evidence]] The system shall refuse to answer when retrieved evidence is insufficient.

### Citation allow-list

[[GOLD:qa-citations]] The system shall cite only chunk identifiers from the retrieved allow-list.

### Prompt injection

[[GOLD:qa-injection]] The system shall treat document text as untrusted data and must not obey embedded jailbreak instructions.

## Requirements extraction

### Modal statements

[[GOLD:extract-modals]] The system shall extract shall, must, should, and may statements as requirements.

### Provenance

[[GOLD:extract-provenance]] The system shall attach source quotes and heading paths to every extracted requirement.

### Export

[[GOLD:extract-export]] The system shall export accepted requirements as JSON and CSV.

## Version comparison

### Alignment

[[GOLD:compare-align]] The system shall align requirements across document versions by identifier or statement similarity.

### Change categories

[[GOLD:compare-categories]] The system shall classify requirement changes as added, removed, clarified, or behavior changed.

## Retention and security

### Retention window

[[GOLD:retention-days]] The system shall delete source document bytes after the configured retention period of 365 days.

### API keys hashed

[[GOLD:security-keys]] The system shall store API keys only as cryptographic hashes.

### Rate limiting

[[GOLD:security-ratelimit]] The system shall apply Redis-backed rate limits to sensitive routes in hosted mode.

## Performance

### Search latency

[[GOLD:perf-search]] The system shall respond to search queries within two hundred milliseconds at p95 under the stub backend.

### Chunk size

[[GOLD:perf-chunks]] Large documents shall be split into chunks of roughly six hundred to nine hundred tokens.

## Observability

### Health endpoints

[[GOLD:ops-health]] The system shall expose separate liveness and readiness HTTP endpoints.

### Correlation IDs

[[GOLD:ops-correlation]] The system shall attach a request correlation identifier to structured logs.
