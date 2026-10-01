#!/usr/bin/env python3
"""Verify externally executed CFA FRA legacy retirement against a reviewed plan."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import (
    LegacyRetirementExecutionError,
    build_legacy_retirement_plan,
    retirement_execution_receipt_payload,
    retirement_plan_payload,
    verify_legacy_retirement_execution,
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
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    inventory = _load(args.inventory)
    readiness = _load(args.readiness)
    plan = build_legacy_retirement_plan(inventory, readiness)
    supplied_plan = _load(args.plan)
    if supplied_plan != retirement_plan_payload(plan):
        raise LegacyRetirementExecutionError(
            "supplied reviewed plan does not match current inventory/readiness"
        )

    receipt = verify_legacy_retirement_execution(
        plan,
        inventory,
        readiness,
        _load(args.evidence),
    )
    payload = retirement_execution_receipt_payload(receipt)
    rendered = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")

    print(rendered, end="")
    print(f"Execution receipt SHA-256: {receipt.receipt_sha256}")
    print(f"Verified observations: {len(receipt.observations)}")
    print("External retirement execution: VERIFIED")
    print("Frozen oracle mutation: FORBIDDEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
