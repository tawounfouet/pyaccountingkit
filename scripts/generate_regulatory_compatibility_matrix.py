#!/usr/bin/env python3
"""Generate the capability-scoped REGULATORY_COMPATIBILITY_MATRIX.json."""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

from pyaccountingkit.integrations.regulatory_framework import (
    baseline_profiles,
    regulatory_compatibility_matrix_payload,
)

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "REGULATORY_COMPATIBILITY_MATRIX.json"


def _project_version() -> str:
    payload = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def generate_payload() -> dict[str, object]:
    version = _project_version()
    return regulatory_compatibility_matrix_payload(
        version,
        baseline_profiles(version),
    )


def _render(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=TARGET)
    args = parser.parse_args()

    rendered = _render(generate_payload())
    if args.check:
        if not args.output.is_file():
            raise SystemExit(f"regulatory compatibility matrix missing: {args.output}")
        if args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit("REGULATORY_COMPATIBILITY_MATRIX.json is stale")
        print("REGULATORY_COMPATIBILITY_MATRIX.json: OK")
        return 0

    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
