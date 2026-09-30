#!/usr/bin/env python3
"""Qualify CFA FRA MIG-13 legacy-retirement readiness."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import (
    LegacyRetirementEvidence,
    LegacyRetirementGate,
    MigrationRouting,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "tests" / "consumer" / "cfa_fra" / "RETIREMENT_EVIDENCE.json"


def _load_manifest() -> Mapping[str, object]:
    return cast(
        Mapping[str, object],
        json.loads(MANIFEST_PATH.read_text(encoding="utf-8")),
    )


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"expected true/false, got {value!r}")


def _job_green(result: str) -> bool:
    return result.strip().lower() == "success"


def qualify(
    *,
    test_result: str,
    django_adapter_result: str,
    sqlalchemy_adapter_result: str,
    consumer_e2e_green: bool,
    identities_traceable: bool,
    regulatory_authority_replaced: bool,
    output: Path | None = None,
) -> int:
    manifest = _load_manifest()
    if manifest.get("schema_version") != "5":
        raise ValueError("MIG-13 retirement evidence must use schema_version='5'")
    if manifest.get("routing_profile") != "target_only":
        raise ValueError("MIG-13 retirement requires routing_profile='target_only'")

    routing = MigrationRouting.target_only()
    if not routing.is_target_only():
        raise RuntimeError("target-only routing profile unexpectedly exposes legacy paths")

    evidence = LegacyRetirementEvidence(
        golden_parity_green=_job_green(test_result),
        production_adapters_green=(
            _job_green(django_adapter_result) and _job_green(sqlalchemy_adapter_result)
        ),
        consumer_e2e_green=consumer_e2e_green,
        identities_traceable=identities_traceable,
        regulatory_authority_replaced=regulatory_authority_replaced,
    )
    decision = LegacyRetirementGate().evaluate(routing, evidence)

    raw_expected = manifest.get("expected_blockers")
    if not isinstance(raw_expected, list) or not all(
        isinstance(item, str) for item in raw_expected
    ):
        raise ValueError("retirement manifest expected_blockers must be a string list")
    expected_blockers = tuple(sorted(cast(list[str], raw_expected)))

    report = {
        "routing_target_only": routing.is_target_only(),
        "ready": decision.ready,
        "blockers": list(decision.blockers),
        "expected_blockers": list(expected_blockers),
        "evidence": {
            "golden_parity_green": evidence.golden_parity_green,
            "production_adapters_green": evidence.production_adapters_green,
            "consumer_e2e_green": evidence.consumer_e2e_green,
            "identities_traceable": evidence.identities_traceable,
            "regulatory_authority_replaced": evidence.regulatory_authority_replaced,
        },
    }

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")

    if decision.blockers != expected_blockers:
        print(
            "CFA FRA retirement blocker set changed; review MIG-13 evidence.",
            file=sys.stderr,
        )
        print(payload, end="", file=sys.stderr)
        return 1

    if decision.ready != (not expected_blockers):
        print("retirement readiness and expected blocker set disagree", file=sys.stderr)
        print(payload, end="", file=sys.stderr)
        return 1

    print(payload, end="")
    if decision.ready:
        print("CFA FRA legacy retirement: READY")
    else:
        print("CFA FRA legacy retirement: QUALIFIED WITH EXPLICIT BLOCKERS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-result", required=True)
    parser.add_argument("--django-adapter-result", required=True)
    parser.add_argument("--sqlalchemy-adapter-result", required=True)
    parser.add_argument("--consumer-e2e-green", required=True)
    parser.add_argument("--identities-traceable", required=True)
    parser.add_argument("--regulatory-authority-replaced", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    return qualify(
        test_result=args.test_result,
        django_adapter_result=args.django_adapter_result,
        sqlalchemy_adapter_result=args.sqlalchemy_adapter_result,
        consumer_e2e_green=_parse_bool(args.consumer_e2e_green),
        identities_traceable=_parse_bool(args.identities_traceable),
        regulatory_authority_replaced=_parse_bool(args.regulatory_authority_replaced),
        output=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
