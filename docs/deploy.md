# SpecLens AI — Deployment

## Local developer stack

```bash
cp .env.example .env
make up
make smoke
cd apps/web && npm install && npm run dev
```

- API: http://127.0.0.1:8000
- Web (Vite): http://127.0.0.1:5173 (proxies `/api` → API)
- Bootstrap key: `speclens-local-dev-key` (rotate before any shared host)

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
