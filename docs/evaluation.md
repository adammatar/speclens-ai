# SpecLens AI - Evaluation

Phase 1 scaffolds the `evals/` tree only. The evaluation harness (`make eval`, datasets, graders, CI thresholds) is Phase 7.

## Layout

```
evals/
├── datasets/    # Versioned JSONL question / extraction sets
├── expected/    # Gold labels and citation expectations
└── reports/     # Generated JSON/HTML outputs (gitignored)
```

## Principles (from the technical plan)

- Measure retrieval separately from generation.
- Track citation precision, unsupported-claim rate, latency, and cost.
- Block regressions in CI once thresholds exist.

No LangChain. Prefer pytest + JSONL datasets for the first harness.
