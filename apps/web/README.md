# SpecLens Web (React + Vite)

Browser UI for the SpecLens FastAPI API.

## Local development

```bash
# API stack running on host :8001 (make up)
cd apps/web
npm install
npm run dev   # http://127.0.0.1:5173 (proxies /api → :8001)
```

Sign in with the local bootstrap API key (`speclens-local-dev-key`). The key is stored in `sessionStorage` only — it is never embedded in the production bundle.

## Build

```bash
npm run build
npm run preview
```

## Production image

Built by `infra/compose.prod.yaml` (nginx serving `dist/` and proxying `/api` to the API service).
