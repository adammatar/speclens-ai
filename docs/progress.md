# SpecLens AI - Progress

## Phase 0-9

**Status:** Complete (approved) - PRs #1-#9

---

## Phase 10 - Portfolio packaging

**Status:** Complete (awaiting review / merge)

**Date:** 2026-11-09

**Branch:** `cursor/phase10-portfolio-packaging-018c`

**PR:** https://github.com/adammatar/speclens-ai/pull/10

### Architecture and implementation decisions

1. **Portfolio pack** under `docs/portfolio/`: architecture SVG, technical write-up (eval/perf/security + contribution), screenshots, demo video.
2. **Deterministic media capture** via `scripts/capture_portfolio_media.mjs` (Playwright Chromium) with password-manager features disabled — avoids flaky GUI click agents and Chrome “Save password?” overlays.
3. **Sign-in field** uses `type="text"` (API key, not a password) so browsers do not treat it as a credential save target.
4. **README polish** links architecture, screenshots, portfolio write-up, deploy/eval/security docs, and contribution statement.
5. No confidential customer documents; demo corpus remains synthetic fixtures.

### Acceptance criteria (technical-plan exit criteria)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Architecture diagram published | Yes | `docs/portfolio/architecture.svg` (+ README embed) |
| Screenshots + demo video | Yes | `docs/portfolio/screenshots/01–08` + `media/demo-walkthrough.webm` (verified: no password modal) |
| Technical write-up + eval/perf/security | Yes | `docs/portfolio/write-up.md` |
| Individual contribution statement | Yes | write-up + README |
| No confidential samples | Yes | synthetic demo only; capture script uses demo_reset seed |

### Changed files (highlights)

```text
README.md
.gitignore
apps/web/package.json / package-lock.json
apps/web/src/pages/SignInPage.tsx
docs/portfolio/**
docs/progress.md
scripts/capture_portfolio_media.mjs
```

### Commands / results

```text
demo_reset.sh                         -> succeeded
apps/web build + preview              -> ok
node scripts/capture_portfolio_media.mjs -> 8 screenshots + demo webm
videoReview                           -> no Save-password modal; full page flow OK
```

**Failures:** none after redo with Playwright capture.

### Explicit stop

Portfolio packaging complete. No further product phase planned in the Phase 0–10 technical plan beyond this packaging handoff.

### Remaining risks

1. Demo video is WebM (Playwright native); convert to MP4 externally if a host requires it.
2. Offline eval metrics are stub-backend / synthetic — write-up states the caveat.
3. Playwright is a web `devDependency` for media regeneration only; not required to run the product.
