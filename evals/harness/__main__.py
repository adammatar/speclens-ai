"""python -m evals.harness"""

from __future__ import annotations

import argparse
from pathlib import Path

from evals.harness.runner import DEFAULT_BASELINE, DEFAULT_OUT, run_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="SpecLens evaluation harness")
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Exit non-zero when thresholds fail (CI blocking mode)",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--no-baseline", action="store_true")
    args = parser.parse_args()
    run_eval(
        out_dir=args.out_dir,
        baseline_path=None if args.no_baseline else args.baseline,
        enforce=args.enforce,
    )


if __name__ == "__main__":
    main()
