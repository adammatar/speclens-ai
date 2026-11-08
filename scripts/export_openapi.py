#!/usr/bin/env python3
"""Export the FastAPI OpenAPI schema for TypeScript contract generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

from app.main import create_app  # noqa: E402


def main() -> None:
    app = create_app()
    schema = app.openapi()
    out_dir = ROOT / "packages" / "contracts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "openapi.json"
    out_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
