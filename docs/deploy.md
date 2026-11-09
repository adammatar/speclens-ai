# SpecLens AI — Deployment

## Local developer stack

```bash
cp .env.example .env
make up
make smoke
cd apps/web && npm install && npm run dev
```

- API: http://127.0.0.1:8001 (mapped from container `:8000`; avoids Cursor binding `:8000`)
- Web (Vite): http://127.0.0.1:5173 (proxies `/api` → API on `:8001`)
- Bootstrap key: `speclens-local-dev-key` (rotate before any shared host)

## Gemini free tier (cited chat)

SpecLens supports Google AI Studio via the OpenAI-compatible Chat Completions API.

1. Create an API key in [Google AI Studio](https://aistudio.google.com/apikey) — **keep it local; never paste it into chat or commit it**.
2. In repo-root `.env` (copy from `.env.example` if needed):

```bash
OPENAI_API_KEY=your-gemini-key-here
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
GENERATION_BACKEND=openai_compat
GENERATION_MODEL=gemini-3.8-flash
# embeddings/extraction can stay stub for first demos (Hebrew-aware stub + simple FTS)
EMBEDDING_BACKEND=stub
EXTRACTION_BACKEND=stub
# Optional Gemini extraction (same key/base URL):
# EXTRACTION_BACKEND=openai_compat
# EXTRACTION_MODEL=gemini-3.8-flash
# Stronger multilingual embeddings (needs OpenAI key; keeps Vector dims=256):
# EMBEDDING_BACKEND=openai
# EMBEDDING_MODEL=text-embedding-3-small
# EMBEDDING_DIMS=256
# EMBEDDING_SEND_DIMENSIONS=true
# OPENAI_BASE_URL=https://api.openai.com/v1
```

3. Confirm these four lines are **uncommented and set** (not left as comments / not `stub`):

```bash
grep -E '^(OPENAI_API_KEY|OPENAI_BASE_URL|GENERATION_BACKEND|GENERATION_MODEL)=' .env | sed 's/\(OPENAI_API_KEY=\).*/\1***/'
```

4. Recreate containers so they reload `.env`: `make down && make up && make smoke`
5. Confirm Dashboard shows `stub/openai_compat/stub` (embedding / generation / extraction).
6. Verify inside the API container:

```bash
docker compose --env-file .env -f infra/compose.yaml exec api printenv GENERATION_BACKEND
curl -s http://127.0.0.1:8001/api/v1/meta
```

Should print `openai_compat`, and host `/meta` must match (not `stub`). If host still shows stub while the container is correct, something else is bound to the API port (historically Cursor on `:8000`).

Rate limits apply on the free tier; if requests fail, wait and retry or check AI Studio quotas.

## Hebrew / multilingual

- UI: EN/HE toggle in the top bar (and Settings). Hebrew sets `dir=rtl`.
- Chat answers follow the **question language** (prompt rule).
- Lexical search uses Postgres FTS config `simple` (Hebrew tokens kept).
- Stub embedder/extractor understand Unicode + Hebrew modals (`חייב`, `חובה`, `אסור`, …).
- Demo files: `demos/hebrew-john-biography.md`, `demos/hebrew-access-control-v1.md` / `v2.md` (compare).

### Why sign-in asks for a “workspace access key”

That field is **not** your Gemini/OpenAI key. SpecLens protects the API with a workspace API key (`Authorization: Bearer …`). Locally the seeded key is `speclens-local-dev-key`. Your LLM provider key stays in server `.env` as `OPENAI_API_KEY`.

## Production-style Compose

```bash
docker compose -f infra/compose.prod.yaml up -d --build
curl -sf http://127.0.0.1:8080/api/v1/health
curl -sf http://127.0.0.1:8080/api/v1/ready
# open http://127.0.0.1:8080 — sign in with an API key
```

Notes:

- Postgres and Redis ports are **not** published.
- `web` (nginx) serves the React build and reverse-proxies `/api` to `api`.
- Set a strong `POSTGRES_PASSWORD` and replace the bootstrap API key before sharing.
- Optional `SENTRY_DSN` is reserved for error tracking (wire SDK when hosting).

### HTTPS

Terminate TLS in front of `web` with your load balancer, Caddy, or Traefik. The container listens on HTTP `:80` by design so the edge owns certificates.

### Monitoring

- Liveness: `GET /api/v1/health`
- Readiness: `GET /api/v1/ready` (fails closed if Postgres is down)
- Point uptime checks at both; alert on non-200 ready.
- Application logs are structured JSON from the API/worker containers.

## Migrations and rollback

```bash
# forward
docker compose -f infra/compose.prod.yaml exec api alembic upgrade head

# show current
docker compose -f infra/compose.prod.yaml exec api alembic current

# rollback one revision (use with care)
docker compose -f infra/compose.prod.yaml exec api alembic downgrade -1
```

Always take a backup before downgrade on shared data.

## Backup and restore

### Backup

```bash
docker compose -f infra/compose.prod.yaml exec -T postgres \
  pg_dump -U speclens speclens > backup-$(date +%Y%m%d).sql
docker compose -f infra/compose.prod.yaml cp api:/data/storage ./backup-storage
```

For the local dev stack, use `infra/compose.yaml` and the same `pg_dump` / copy pattern against `data/storage`.

### Restore (scratch verification)

```bash
docker compose -f infra/compose.prod.yaml down -v
docker compose -f infra/compose.prod.yaml up -d --build
# wait for healthy api
docker compose -f infra/compose.prod.yaml exec -T postgres \
  psql -U speclens -d speclens < backup-YYYYMMDD.sql
docker compose -f infra/compose.prod.yaml cp ./backup-storage/. api:/data/storage/
curl -sf http://127.0.0.1:8080/api/v1/ready
```

## Demo reset

```bash
./scripts/demo_reset.sh
```

Deletes demo workspace documents via SQL (default workspace) and re-seeds the sample Markdown fixture through the authenticated API. Safe for local/demo only — not for customer data.

## Confidential samples

Do not publish real customer/SharePoint DOCX files. Demo corpus is limited to synthetic fixtures under `services/api/tests/fixtures/` and generated eval JSONL.
