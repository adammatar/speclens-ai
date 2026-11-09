# SpecLens AI - Progress

## Phase 0-10

**Status:** Complete (merged to `main`) — PRs #1–#11, #13 (Gemini)

---

## UX redesign U0–U6 (iOS-inspired workspace)

**Status:** Implemented on branch (awaiting review)

**Date:** 2026-11-09

**Branch:** `cursor/ux-ios-workspace-redesign-018c`

**Approved scope:** U0–U6 (portfolio UX redesign)

### What shipped

1. **U0** — Merged Gemini `openai_compat` PR #13 into `main`.
2. **U1** — iOS-inspired light theme, top bar shell, Home split layout.
3. **U2** — Document list with search/filter, fixed-height scroll (5 rows + load more), full Documents library, per-doc **New version** upload (keeps latest + previous).
4. **U3** — ChatGPT-style thread with loading bubble, multi-doc chips (≥1 required), plain-language answer cleanup (no raw UUIDs).
5. **U4** — Auto pipeline after upload/version: ingest → extract → optional compare; Requirements/Compare/Evaluation removed from primary nav.
6. **U5** — “What changed?” style questions trigger background version compare summary in chat.
7. **U6** — Progress/docs updated; re-capture portfolio screenshots after merge (run `make portfolio-media` with stack up).

### Architecture decisions

- Primary UX is **Home**: stats + docs | persistent chat (not separate Cited chat page).
- Operator pages (requirements/compare/eval) are backend-capable but hidden from clients.
- Citations remain allow-listed server-side; UI only shows human-readable notes.

### Explicit stop

Awaiting PR review / merge. Portfolio media refresh recommended after merge on a machine with Docker + Playwright.
