#!/usr/bin/env python3
"""Validate the CFA FRA live-cutover evidence contract."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import LiveCutoverEvidence

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "consumer" / "cfa_fra" / "RETIREMENT_EVIDENCE.json"


def _load() -> Mapping[str, object]:
    return cast(Mapping[str, object], json.loads(MANIFEST.read_text(encoding="utf-8")))


def validate() -> list[str]:
    violations: list[str] = []
    payload = _load()

    if payload.get("schema_version") != "2":
        violations.append("live cutover evidence must use schema_version='2'")
    if payload.get("routing_profile") != "target_only":
        violations.append("live cutover evidence requires target_only routing")

    raw_external = payload.get("external_evidence")
    if not isinstance(raw_external, dict):
        return [*violations, "external_evidence must be a JSON object"]

    try:
        evidence = LiveCutoverEvidence.from_mapping(raw_external)
    except (TypeError, ValueError) as exc:
        violations.append(str(exc))
        return violations

    raw_expected = payload.get("expected_blockers")
    if not isinstance(raw_expected, list) or not all(
        isinstance(item, str) for item in raw_expected
    ):
        violations.append("expected_blockers must be a string list")
        return violations

    expected = set(cast(list[str], raw_expected))
    if not evidence.identities_traceable and "evidence:legacy-identities" not in expected:
        violations.append("blocked identity evidence must keep legacy-identities blocker")
    if evidence.identities_traceable and "evidence:legacy-identities" in expected:
        violations.append("attested identity evidence must remove legacy-identities blocker")

    if (
        not evidence.regulatory_authority_replaced
        and "evidence:regulatory-authority" not in expected
    ):
        violations.append(
            "blocked regulatory evidence must keep regulatory-authority blocker"
        )
    if (
        evidence.regulatory_authority_replaced
        and "evidence:regulatory-authority" in expected
    ):
        violations.append(
            "attested regulatory evidence must remove regulatory-authority blocker"
        )

    return violations


def main() -> int:
    violations = validate()
    if violations:
        print("CFA FRA live cutover evidence: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    evidence = LiveCutoverEvidence.from_mapping(_load()["external_evidence"])
    print("CFA FRA live cutover evidence: PASS")
    print(f"Legacy identities attested: {evidence.identities_traceable}")
    print(
        "Regulatory authority attested: "
        f"{evidence.regulatory_authority_replaced}"
    )
    print("PASS records require artifact + SHA-256 + UTC observation + producer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
