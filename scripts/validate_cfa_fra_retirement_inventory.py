#!/usr/bin/env python3
"""Validate the CFA FRA legacy-engine retirement inventory."""

from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import ORACLE_TREE_SHA

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "tests" / "consumer" / "cfa_fra" / "LEGACY_RETIREMENT_INVENTORY.json"
CONSUMER_MATRIX = ROOT / "tests" / "consumer" / "cfa_fra" / "CONSUMER_EVIDENCE_MATRIX.json"

_ALLOWED = {
    "RETIRE_ENGINE",
    "REWIRE_CONSUMER",
    "MIGRATE_PERSISTENCE",
    "KEEP_CONSUMER",
    "FROZEN_ORACLE",
}

_REQUIRED_ENGINE_PATHS = {
    "apps/accounting/services.py",
    "apps/accounting/selectors.py",
    "apps/imports/services.py",
    "apps/reporting/selectors.py",
    "apps/financial_statements/services.py",
    "apps/financial_statements/regulatory.py",
}

_REQUIRED_REWIRE_PATHS = {
    "apps/accounting/views.py",
    "apps/imports/views.py",
    "apps/reporting/views.py",
    "apps/financial_statements/views.py",
    "apps/financial_statements/regulatory_views.py",
    "apps/controls/views.py",
    "apps/closing/views.py",
    "apps/referentials/views.py",
}

_REQUIRED_PERSISTENCE_PATHS = {
    "apps/accounting/models.py",
    "apps/imports/models.py",
    "apps/reporting/models.py",
    "apps/financial_statements/models.py",
    "apps/referentials/models.py",
    "apps/controls/models.py",
    "apps/closing/models.py",
}


def _load(path: Path) -> Mapping[str, object]:
    return cast(Mapping[str, object], json.loads(path.read_text(encoding="utf-8")))


def validate() -> list[str]:
    violations: list[str] = []
    payload = _load(INVENTORY)
    oracle = cast(Mapping[str, object], payload.get("oracle", {}))
    policy = cast(Mapping[str, object], payload.get("policy", {}))

    resource_path = oracle.get("resource_path")
    if not isinstance(resource_path, str) or not resource_path:
        return ["inventory oracle.resource_path must be a non-empty string"]
    resource = ROOT / resource_path

    tree_sha = oracle.get("tree_sha")
    if tree_sha != ORACLE_TREE_SHA:
        violations.append("inventory tree_sha must equal the qualified CFA FRA oracle tree")

    consumer = _load(CONSUMER_MATRIX)
    consumer_oracle = cast(Mapping[str, object], consumer.get("oracle", {}))
    if tree_sha != consumer_oracle.get("tree_sha"):
        violations.append("retirement inventory and consumer matrix must use the same oracle")

    if policy.get("snapshot_is_immutable") is not True:
        violations.append("retirement inventory must keep the bundled snapshot immutable")
    if policy.get("applies_to") != "live-consumer-equivalents":
        violations.append("retirement dispositions must target live consumer equivalents")
    if policy.get("retirement_requires_mig13_ready") is not True:
        violations.append("legacy deletion must remain gated by MIG-13 readiness")

    raw_components = payload.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        return [*violations, "retirement inventory must contain components"]

    entries: dict[str, str] = {}
    paths: list[str] = []
    for raw in raw_components:
        if not isinstance(raw, dict):
            violations.append("retirement inventory components must be JSON objects")
            continue
        item = cast(Mapping[str, object], raw)
        path = item.get("path")
        disposition = item.get("disposition")
        reason = item.get("reason")

        if not isinstance(path, str) or not path:
            violations.append("retirement component path must be non-empty")
            continue
        paths.append(path)
        if not isinstance(disposition, str) or disposition not in _ALLOWED:
            violations.append(f"{path}: invalid retirement disposition {disposition!r}")
            continue
        if not isinstance(reason, str) or not reason.strip():
            violations.append(f"{path}: retirement disposition requires a reason")
        if not (resource / path).is_file():
            violations.append(f"{path}: source anchor does not exist in frozen oracle")
        entries[path] = disposition

    duplicates = sorted(path for path, count in Counter(paths).items() if count > 1)
    if duplicates:
        violations.append(f"duplicate retirement inventory paths: {duplicates!r}")

    for path in sorted(_REQUIRED_ENGINE_PATHS):
        if entries.get(path) != "RETIRE_ENGINE":
            violations.append(f"{path}: duplicate engine surface must be RETIRE_ENGINE")
    for path in sorted(_REQUIRED_REWIRE_PATHS):
        if entries.get(path) != "REWIRE_CONSUMER":
            violations.append(f"{path}: Django endpoint must be REWIRE_CONSUMER")
    for path in sorted(_REQUIRED_PERSISTENCE_PATHS):
        if entries.get(path) != "MIGRATE_PERSISTENCE":
            violations.append(f"{path}: legacy state must be MIGRATE_PERSISTENCE")

    for path, disposition in entries.items():
        if disposition == "RETIRE_ENGINE" and path.endswith(("views.py", "forms.py")):
            violations.append(f"{path}: Django UI boundary cannot be retired as engine code")
        if disposition == "FROZEN_ORACLE" and "/tests/" not in path:
            violations.append(f"{path}: FROZEN_ORACLE entries must be test evidence anchors")

    counts = Counter(entries.values())
    for required in _ALLOWED:
        if counts[required] == 0:
            violations.append(f"retirement inventory has no {required} component")

    return violations


def main() -> int:
    violations = validate()
    if violations:
        print("CFA FRA retirement inventory: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    payload = _load(INVENTORY)
    components = cast(list[Mapping[str, object]], payload["components"])
    counts = Counter(str(item["disposition"]) for item in components)

    print("CFA FRA retirement inventory: PASS")
    print(f"Oracle tree: {ORACLE_TREE_SHA}")
    for disposition in sorted(_ALLOWED):
        print(f"{disposition}: {counts[disposition]}")
    print("Snapshot mutation: forbidden")
    print("Deletion target: live consumer equivalents after MIG-13 readiness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
