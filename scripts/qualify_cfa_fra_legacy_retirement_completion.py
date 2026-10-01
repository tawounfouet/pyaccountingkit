#!/usr/bin/env python3
"""Qualify final CFA FRA L26-C legacy-retirement completion."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import (
    LegacyRetirementCompletionError,
    build_legacy_retirement_plan,
    complete_legacy_retirement,
    retirement_completion_payload,
    retirement_plan_payload,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "tests" / "consumer" / "cfa_fra" / "LEGACY_RETIREMENT_INVENTORY.json"


def _load(path: Path) -> Mapping[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(Mapping[str, object], raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--execution-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    inventory = _load(args.inventory)
    readiness = _load(args.readiness)
    plan = build_legacy_retirement_plan(inventory, readiness)
    if _load(args.plan) != retirement_plan_payload(plan):
        raise LegacyRetirementCompletionError(
            "supplied retirement plan does not match current inventory/readiness"
        )

    completion = complete_legacy_retirement(
        plan,
        inventory,
        readiness,
        _load(args.execution_evidence),
    )
    payload = retirement_completion_payload(completion)
    rendered = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")

    print(rendered, end="")
    print(f"Completion SHA-256: {completion.completion_sha256}")
    print("L26-C legacy retirement: COMPLETE")
    print("0.6.0rc1 qualification: ELIGIBLE")
    print("Canonical live completion still requires live consumer evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
