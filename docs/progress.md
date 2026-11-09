# SpecLens AI - Progress

## Phase 0-9

**Status:** Complete (approved) - PRs #1-#9

---

## Phase 10 - Portfolio packaging

**Status:** Complete and re-verified (awaiting review / merge)

**Date:** 2026-11-09

**Branch:** `cursor/phase10-portfolio-packaging-018c`

**PR:** https://github.com/adammatar/speclens-ai/pull/10

### Architecture and implementation decisions

1. **Portfolio pack** at `docs/portfolio/`: architecture SVG, technical write-up (eval table, performance notes, security summary, contribution, case study), screenshots, demo video.
2. **Deterministic media capture** with Playwright (`scripts/capture_portfolio_media.mjs`), Chromium password-manager features disabled — no flaky GUI click agents, no Chrome “Save password?” overlays.
3. **Sign-in** API key field is `type="text"` so browsers do not treat it as a password credential.
4. **README** embeds architecture + screenshots and links deploy/eval/security/portfolio docs.
5. Synthetic demo corpus only (`sample.md` / eval JSONL); bootstrap secrets stay out of the web bundle.

### Acceptance criteria (technical-plan exit criteria)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Architecture diagram | Yes | `docs/portfolio/architecture.svg` (+ README) |
| Product screenshots | Yes | `docs/portfolio/screenshots/01–08.webp` (dashboard verified clean of password UI) |
| ~2 min demo video | Yes | `docs/portfolio/media/demo-walkthrough.webm` (prior videoReview: no password modal) |
| Public technical write-up | Yes | `docs/portfolio/write-up.md` |
| Evaluation results | Yes | write-up metrics table; `make eval` gates passed on re-verify |
| Performance notes | Yes | write-up “Performance notes” |
| Security summary | Yes | write-up + `docs/security.md` |
| Individual contribution | Yes | write-up + README |
| README setup + architecture | Yes | root `README.md` |
| Portfolio case study | Yes | write-up case-study + résumé line |
| No confidential samples | Yes | fixtures only; `NO_KEY_IN_DIST` on web build |

### Changed files (vs Phase 9)

```text
.gitignore
Makefile
README.md
apps/web/package-lock.json
apps/web/package.json
apps/web/src/pages/SignInPage.tsx
docs/portfolio/README.md
docs/portfolio/architecture.svg
docs/portfolio/media/demo-walkthrough.webm
docs/portfolio/screenshots/01-signin.webp
docs/portfolio/screenshots/02-dashboard.webp
docs/portfolio/screenshots/03-documents.webp
docs/portfolio/screenshots/04-document-detail.webp
docs/portfolio/screenshots/05-chat.webp
docs/portfolio/screenshots/06-requirements.webp
docs/portfolio/screenshots/07-compare.webp
docs/portfolio/screenshots/08-settings.webp
docs/portfolio/write-up.md
docs/progress.md
scripts/capture_portfolio_media.mjs
```

### Commands / results (re-verification 2026-11-09)

```text
ruff check / format --check               -> pass (114 files)
mypy                                      -> Success (72 source files)
pytest                                    -> 50 passed, 1 warning
apps/web npm run build                    -> pass; no bootstrap key in dist/
python -m evals.harness                   -> all gates passed
GitHub CI (PR #10)                        -> lint/pytest, eval, compose smoke SUCCESS
Asset inventory                           -> 8 screenshots + demo webm + architecture.svg present
```

**Failures:** none on re-verify.

### Explicit stop

The Phase 0–10 technical plan is complete. **No next product phase is started.** Optional follow-up work below awaits explicit approval.

### Remaining risks

1. Demo video is WebM; some hosts prefer MP4 (convert externally if needed).
2. Eval numbers are stub-backend / synthetic — useful for regression, not live-LLM marketing claims.
3. Playwright is a web `devDependency` for regenerating media only.
4. Operator UX pages remain thin (UUID fields in places) if this product is taken beyond portfolio scope.

---

## Optional follow-up plan (proposed) - Post-plan hardening

**Do not execute until explicitly approved.** The original technical plan ends at Phase 10.

### Goal

Optional hardening and polish beyond the portfolio handoff — only if you want to continue the product.

### Scope candidates (pick explicitly if approved)

1. Redis-backed rate limits; rotate/disable bootstrap API key path for hosted demos.
2. Richer React pickers (document/version selectors) for chat/compare/requirements.
3. Wire optional Sentry SDK from `SENTRY_DSN`.
4. Convert demo WebM → MP4 and add a short public case-study page if publishing outside GitHub.
5. Live OpenAI backend smoke profile (non-CI) with cost/latency measurement.

### Non-goals unless requested

- Enterprise SSO/SCIM
- Electron packaging
- New AI feature verticals

### Exit criteria (if executed)

| Criterion | Proof |
| --- | --- |
| Chosen items implemented | Tests + docs update |
| Portfolio media still clean | Re-run `capture_portfolio_media.mjs` |
| No confidential samples | Corpus check |

### Implementation sketch

1. Branch `cursor/postplan-<focus>-018c` from Phase 10.
2. Implement only the approved subset; PR; stop.
