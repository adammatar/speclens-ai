# Portfolio pack

Assets for presenting SpecLens AI. Screenshots and the demo video are captured with
`scripts/capture_portfolio_media.mjs` (Playwright, password-manager UI disabled) — not
manual browser automation — so Chrome “Save password?” bubbles never appear.

All media uses **synthetic fixtures** and **deterministic stub backends** only. No customer
documents, real credentials, or paid-provider calls are required. Evaluation scores shown
in screenshots are **synthetic regression controls**, not production model accuracy.

| Asset | Path |
| --- | --- |
| Architecture diagram | [`architecture.svg`](./architecture.svg) |
| Technical write-up | [`write-up.md`](./write-up.md) |
| Screenshots | [`screenshots/`](./screenshots/) |
| Demo walkthrough | [`media/demo-walkthrough.webm`](./media/demo-walkthrough.webm) |

### Current screenshot set (refreshed 2026-11-10)

| File | View |
| --- | --- |
| `01-signin.webp` | Sign-in (SpecLens AI + EN/HE toggle) |
| `02-home.webp` | Home split workspace |
| `03-documents.webp` | Documents library (Demo Sample Spec) |
| `04-document-detail.webp` | Document detail / version history |
| `05-chat.webp` | Cited chat with assistant answer + source indicator |
| `06-requirements.webp` | Populated Requirements (extracted rows + provenance) |
| `07-compare.webp` | Populated Compare (visible requirement changes) |
| `08-evaluation.webp` | Evaluation dashboard (metrics + Synthetic / stub badge) |
| `09-settings.webp` | Settings |
| `10-hebrew-ui.webp` | Hebrew RTL product screen (Requirements) |
| `media/demo-walkthrough.webm` | Short product walkthrough |
| `architecture.svg` | System architecture diagram (UTF-8 SVG) |
| `write-up.md` | Technical write-up |

## Rebuild demo + regenerate media

Requires the local Compose stack (Postgres, Redis, API, worker) with stub backends — never
OpenAI/Gemini for portfolio capture.

```bash
# 1) Start local stack
make up

# 2) Optional: refresh stub evaluation report (regression controls only)
make eval EVAL_ENFORCE=1

# 3) Seed a complete deterministic demo workspace
#    (Demo Sample Spec v1+v2, extraction, comparison, wait for jobs)
make demo-reset

# 4) Build web + serve preview (proxies /api → http://127.0.0.1:8001)
cd apps/web && npm run build
npm run preview -- --host 127.0.0.1 --port 4173 --strictPort

# 5) Capture screenshots + walkthrough (fails if expected data is missing)
# other terminal, from repo root:
cd apps/web && npx playwright install chromium
node scripts/capture_portfolio_media.mjs
# or:
make portfolio-media
```

`make demo-reset` is idempotent: it clears the default local workspace, uploads synthetic
fixtures (`services/api/tests/fixtures/sample.md` + `demos/demo-sample-spec-v2.md`), waits for
ingestion/embeddings/extraction/comparison, and fails with a clear message on job timeout.

Capture assertions refuse empty Requirements/Compare/Chat/Evaluation/Hebrew screens.
Preview proxies `/api` → `http://127.0.0.1:8001`. The default local key
`speclens-local-dev-key` is for localhost demos only and must never appear as a production secret.
