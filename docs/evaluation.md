# SpecLens AI - Evaluation

Phase 7 delivers a local, version-controlled offline evaluation harness.

## Layout

```
evals/
├── datasets/          # Versioned JSONL suites (synthetic fixtures)
├── baselines/         # Checked-in baseline metrics for prompt/model diffs
├── harness/           # Graders + runner (`python -m evals.harness`)
├── thresholds.json    # Gate definitions (advisory by default)
├── reports/           # Generated latest.json/html (gitignored except .gitkeep)
└── tests/             # Harness unit tests
artifacts/eval/        # make eval output (gitignored)
```

## Suites

- Retrieval (Recall@10, MRR)
- QA citations (precision, coverage, unsupported-claim rate)
- Requirement extraction (statement F1)
- Version compare alignment accuracy
- Insufficient-evidence accuracy
- Prompt-injection resistance

## Commands

```bash
make eval                 # advisory thresholds; writes JSON + HTML
make eval EVAL_ENFORCE=1  # fail the process when gates fail
python3 scripts/generate_eval_datasets.py
python3 scripts/export_eval_examples.py   # optional DB gold import
```

## CI

The `Evaluation harness` job runs `make eval` after lint/tests. It is advisory unless repository variable `EVAL_ENFORCE=true`.

## Principles

- Measure retrieval separately from generation.
- Track citation precision, unsupported-claim rate, latency/cost stubs as the suite grows.
- No LangChain. Synthetic fixtures only in the committed datasets.
