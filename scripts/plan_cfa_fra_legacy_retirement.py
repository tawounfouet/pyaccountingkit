#!/usr/bin/env python3
"""Build a non-executing CFA FRA legacy-retirement plan from MIG-13 READY evidence."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import (
    LegacyRetirementAction,
    build_legacy_retirement_plan,
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
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plan = build_legacy_retirement_plan(
        _load(args.inventory),
        _load(args.readiness),
    )
    payload = retirement_plan_payload(plan)
    rendered = json.dumps(payload, indent=2, sort_keys=False) + "\n"

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")

    print(rendered, end="")
    print(f"Plan SHA-256: {plan.plan_sha256}")
    for action in LegacyRetirementAction:
        print(f"{action.value}: {len(plan.by_action(action))}")
    print("Execution: NOT PERFORMED")
    print("Frozen oracle mutation: FORBIDDEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
