# Portfolio pack

Assets for presenting SpecLens AI. Screenshots and the demo video are captured with
`scripts/capture_portfolio_media.mjs` (Playwright, password-manager UI disabled) — not
manual browser automation — so Chrome “Save password?” bubbles never appear.

| Asset | Path |
| --- | --- |
| Architecture diagram | [`architecture.svg`](./architecture.svg) |
| Technical write-up | [`write-up.md`](./write-up.md) |
| Screenshots | [`screenshots/`](./screenshots/) |
| Demo walkthrough | [`media/demo-walkthrough.webm`](./media/demo-walkthrough.webm) |

### Current screenshot set (refreshed 2026-11-09)

| File | View |
| --- | --- |
| `01-signin.webp` | Sign-in (SpecLens AI + EN/HE toggle) |
| `02-home.webp` | Home split workspace |
| `03-documents.webp` | Documents library |
| `04-document-detail.webp` | Document detail / versions |
| `05-chat.webp` | Cited chat on Home |
| `06-settings.webp` | Settings |
| `07-hebrew-ui.webp` | Hebrew RTL settings |

## Regenerate media

```bash
make up && make demo-reset
cd apps/web && npm run build && npm run preview -- --host 127.0.0.1 --port 4173 --strictPort
# other terminal:
node scripts/capture_portfolio_media.mjs
# or:
make portfolio-media
```

Requires Playwright Chromium once: `cd apps/web && npx playwright install chromium`.
Preview proxies `/api` → `http://127.0.0.1:8001`.
