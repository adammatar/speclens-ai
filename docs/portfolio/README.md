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

## Regenerate media

```bash
make up && make demo-reset
cd apps/web && npm run build && npm run preview -- --host 127.0.0.1 --port 4173
# other terminal:
node scripts/capture_portfolio_media.mjs
```

Requires Playwright Chromium once: `cd apps/web && npx playwright install chromium`.
