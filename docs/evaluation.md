# SpecLens AI - Evaluation

The evaluation harness measures SpecLens **application pipelines** on synthetic fixtures.

Predictions are **generated at runtime** by ingest → embed → retrieve → QA / extract / compare.
Gold datasets under `evals/datasets/` must not contain `predicted_*` fields.

## Modes

| Mode | Command | Provider keys | CI |
| --- | --- | --- | --- |
| **stub** (default) | `make eval` / `EVAL_MODE=stub` | Not required | Enforced |
| **live** | `EVAL_MODE=live make eval` | OpenAI / compatible | Optional |

Stub results are **deterministic synthetic/backend checks**. They are **not** production accuracy claims.

## Layout

```
evals/
├── corpus/            # Synthetic markdown fixtures with [[GOLD:id]] markers
├── datasets/          # Gold-only JSONL (questions, labels, corpus refs)
├── baselines/         # Metrics from a real prior stub run
├── harness/           # Pipeline executor + graders + runner
├── thresholds.json    # Enforced gates
├── reports/           # latest.json/html (generated)
└── tests/             # Includes regression: bad retrieval fails thresholds
artifacts/eval/        # make eval output
```

## Metrics

- Retrieval Recall@5, Recall@10, MRR
- Citation precision (allow-list), coverage, unsupported-claim rate
- Requirement extraction precision / recall / F1
- Comparison alignment accuracy
- Insufficient-evidence accuracy
- Prompt-injection resistance
- Latency p50 / p95 (and token/cost fields when available)

## Commands

```bash
make eval                 # stub mode; writes artifacts/eval/report.{json,html}
make eval EVAL_ENFORCE=1  # fail the process when gates fail
EVAL_MODE=live make eval  # optional live providers
python3 scripts/generate_eval_datasets.py   # regenerate gold-only JSONL
```

Reports include mode, backends/models, prompt versions, dataset version, git commit,
sample counts, per-example failures, baseline deltas, and an explicit synthetic/stub caveat.

## Principles

- Measure retrieval separately from generation.
- Never commit prefilled predictions in gold datasets.
- Never require a paid provider for normal CI.
- Preserve synthetic-only public data.
