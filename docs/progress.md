# SpecLens AI - Progress

## Phase 0-10 + UX redesign

**Status:** Complete on `main` (PRs #1–#11, #13 Gemini, #14 iOS Home workspace)

---

## Hebrew / multilingual (H1–H4)

**Status:** Implemented (awaiting review)

**Date:** 2026-11-09

**Branch:** `cursor/hebrew-i18n-multilingual-018c`

### What shipped

1. **H1** — Unicode stub embeddings; answering prompt answers in the user’s language; FTS switched to Postgres `simple`; docs for OpenAI multilingual embeddings at dims=256.
2. **H2** — Hebrew modals in stub extraction; `openai_compat` extraction backend; Hebrew-aware compare tokenization / breaking heuristics; extraction prompt updated.
3. **H3** — EN/HE UI toggle (top bar + Settings) with RTL; clearer “workspace access key” copy (not the LLM key).
4. **H4** — Hebrew demos (`hebrew-john-biography`, `hebrew-access-control` v1/v2) + unit tests.

### Explicit stop

Awaiting PR review / merge.
