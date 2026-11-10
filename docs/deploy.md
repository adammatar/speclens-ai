# SpecLens AI — Deployment

## Environments at a glance

| Concern | Local / CI | Staging / production-style Compose |
| --- | --- | --- |
| Compose file | `infra/compose.yaml` | `infra/compose.prod.yaml` |
| `POSTGRES_PASSWORD` | Default `speclens_dev_password` OK | **Required**; no insecure fallback |
| Bootstrap key | `make up` runs `bootstrap-local` | **Never** run bootstrap-local |
| API keys | Documented local key for DX | `python -m app.cli keys create …` |
| `AUTH_REQUIRED` | true (tests may override) | Must be true (startup refuses false) |
| Rate limits | Memory fallback if Redis down | Redis required |
| Retention sweeps | Off (`RETENTION_SWEEP_ENABLED=false`) | Enable explicitly when ready |
| Eval | Stub `make eval EVAL_ENFORCE=1` | Same; optional `EVAL_MODE=live` |

## Local developer stack

```bash
cp .env.example .env
make up
make smoke
cd apps/web && npm install && npm run dev
```

- API: http://127.0.0.1:8001
- Web (Vite): http://127.0.0.1:5173
- Local bootstrap key (DX only): `speclens-local-dev-key` — **never advertise for hosted deployments**

## Creating and rotating production API keys

```bash
# Inside the API container / venv (hosted)
python -m app.cli keys create --email you@example.com --name prod
python -m app.cli keys list
python -m app.cli keys rotate --id <uuid>
python -m app.cli keys disable --id <uuid>
python -m app.cli check-startup
```

Plaintext is shown **once**. Only SHA-256 hashes are stored. Avoid logging keys.

## Gemini / OpenAI-compatible backends

See `.env.example`. Provider keys stay in server env only — never in `apps/web`.

## Production-style Compose

Required secrets (fail-fast if missing/insecure):

- `POSTGRES_PASSWORD` — strong; not `speclens_dev_password`
- High-entropy API key created via CLI (bootstrap key must stay inactive)
- `AUTH_REQUIRED=true`
- Optional: `SENTRY_DSN`, LLM provider keys

```bash
export POSTGRES_PASSWORD='replace-with-strong-secret'
docker compose -f infra/compose.prod.yaml up -d --build
curl -sf http://127.0.0.1:8080/api/v1/health
curl -sf http://127.0.0.1:8080/api/v1/ready
```

Migrations run on API start; `check-startup` refuses weak passwords, disabled auth, or an active local bootstrap key. Production Compose does **not** run `bootstrap-local`.

### Public-demo safety checklist

- [ ] Strong `POSTGRES_PASSWORD`
- [ ] No `speclens-local-dev-key` active
- [ ] `AUTH_REQUIRED=true`
- [ ] Synthetic demo docs only
- [ ] Provider keys not in frontend bundle / README
- [ ] Retention / Sentry reviewed for privacy

### HTTPS

Terminate TLS in front of `web` (load balancer / Caddy / Traefik). Container listens on HTTP `:80`.

### Monitoring

- Liveness: `GET /api/v1/health`
- Readiness: `GET /api/v1/ready` (DB required; Redis required when hosted)
- Correlate logs with `X-Request-ID`
- Worker health: monitor Celery/Redis queue depth separately
- Optional Sentry when `SENTRY_DSN` is set (redacts bodies/secrets)

## Backup and restore

```bash
docker compose -f infra/compose.prod.yaml exec -T postgres \
  pg_dump -U speclens speclens > backup-$(date +%Y%m%d).sql
docker compose -f infra/compose.prod.yaml cp api:/data/storage ./backup-storage
```

Isolated verification (does not destroy developer data):

```bash
./scripts/verify_backup_restore.sh
```

## Demo reset

```bash
./scripts/demo_reset.sh
```

Synthetic fixtures only — not for customer data.

## Confidential samples

Do not publish real customer/SharePoint DOCX files. Demo corpus is synthetic under `demos/`, `evals/corpus/`, and `services/api/tests/fixtures/`.
