#!/usr/bin/env python3
"""Validate and cryptographically verify CFA FRA live-cutover evidence."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pyaccountingkit.integrations.cfa_fra import (
    CutoverArtifactVerificationError,
    LEGACY_IDENTITIES_SCHEMA,
    LiveCutoverEvidence,
    REGULATORY_AUTHORITY_SCHEMA,
    VerifiedExternalCutoverEvidence,
    VerifiedLiveCutoverEvidence,
    verify_live_cutover_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "consumer" / "cfa_fra" / "RETIREMENT_EVIDENCE.json"


def _load() -> Mapping[str, object]:
    return cast(Mapping[str, object], json.loads(MANIFEST.read_text(encoding="utf-8")))


def _artifact_root(payload: Mapping[str, object]) -> Path:
    raw_policy = payload.get("artifact_policy")
    if not isinstance(raw_policy, dict):
        raise ValueError("live cutover evidence must define artifact_policy")
    policy = cast(Mapping[str, object], raw_policy)

    raw_root = policy.get("root")
    if not isinstance(raw_root, str) or not raw_root.strip():
        raise ValueError("artifact_policy.root must be a non-empty string")
    if policy.get("require_local_materialization") is not True:
        raise ValueError("artifact_policy must require local materialization")
    if policy.get("sha256_verified") is not True:
        raise ValueError("artifact_policy must require SHA-256 verification")
    if policy.get("content_schema_verified") is not True:
        raise ValueError("artifact_policy must require semantic content-schema verification")

    raw_schemas = policy.get("schemas")
    expected_schemas = {
        "legacy_identities": LEGACY_IDENTITIES_SCHEMA,
        "regulatory_authority": REGULATORY_AUTHORITY_SCHEMA,
    }
    if raw_schemas != expected_schemas:
        raise ValueError(
            "artifact_policy.schemas must match the qualified CFA FRA evidence schemas"
        )

    root = (ROOT / raw_root).resolve()
    try:
        root.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("artifact_policy.root must remain inside the repository") from exc
    if not root.is_dir():
        raise ValueError("artifact_policy.root must exist as a directory")
    return root


def _verified_record(record: VerifiedExternalCutoverEvidence) -> dict[str, object]:
    return {
        "status": record.evidence.status.value,
        "artifact": record.evidence.artifact,
        "verified": record.verified,
        "green": record.green,
        "actual_sha256": record.actual_sha256,
    }


def _report(
    evidence: VerifiedLiveCutoverEvidence,
    *,
    artifact_root: Path,
) -> dict[str, object]:
    return {
        "artifact_root": str(artifact_root.relative_to(ROOT)),
        "identities_traceable": evidence.identities_traceable,
        "regulatory_authority_replaced": evidence.regulatory_authority_replaced,
        "records": {
            "legacy_identities": _verified_record(evidence.legacy_identities),
            "regulatory_authority": _verified_record(evidence.regulatory_authority),
        },
    }


def validate() -> tuple[list[str], VerifiedLiveCutoverEvidence | None, Path | None]:
    violations: list[str] = []
    payload = _load()

    if payload.get("schema_version") != "4":
        violations.append("live cutover evidence must use schema_version='4'")
    if payload.get("routing_profile") != "target_only":
        violations.append("live cutover evidence requires target_only routing")

    try:
        artifact_root = _artifact_root(payload)
    except ValueError as exc:
        violations.append(str(exc))
        artifact_root = None

    raw_external = payload.get("external_evidence")
    if not isinstance(raw_external, dict):
        return [*violations, "external_evidence must be a JSON object"], None, artifact_root

    try:
        evidence = LiveCutoverEvidence.from_mapping(raw_external)
    except (TypeError, ValueError) as exc:
        violations.append(str(exc))
        return violations, None, artifact_root

    verified: VerifiedLiveCutoverEvidence | None = None
    if artifact_root is not None:
        try:
            verified = verify_live_cutover_evidence(
                evidence,
                artifact_root=artifact_root,
            )
        except CutoverArtifactVerificationError as exc:
            violations.append(str(exc))

    raw_expected = payload.get("expected_blockers")
    if not isinstance(raw_expected, list) or not all(
        isinstance(item, str) for item in raw_expected
    ):
        violations.append("expected_blockers must be a string list")
        return violations, verified, artifact_root

    if verified is None:
        return violations, verified, artifact_root

    expected = set(cast(list[str], raw_expected))
    if not verified.identities_traceable and "evidence:legacy-identities" not in expected:
        violations.append("unverified identity evidence must keep legacy-identities blocker")
    if verified.identities_traceable and "evidence:legacy-identities" in expected:
        violations.append("verified identity evidence must remove legacy-identities blocker")

    if (
        not verified.regulatory_authority_replaced
        and "evidence:regulatory-authority" not in expected
    ):
        violations.append("unverified regulatory evidence must keep regulatory-authority blocker")
    if verified.regulatory_authority_replaced and "evidence:regulatory-authority" in expected:
        violations.append("verified regulatory evidence must remove regulatory-authority blocker")

    return violations, verified, artifact_root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    violations, evidence, artifact_root = validate()
    if violations:
        print("CFA FRA live cutover evidence: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    if evidence is None or artifact_root is None:
        print("CFA FRA live cutover evidence: incomplete verification", file=sys.stderr)
        return 1

    report = _report(evidence, artifact_root=artifact_root)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    print(payload, end="")
    print("CFA FRA live cutover evidence: PASS")
    print(f"Legacy identities verified: {evidence.identities_traceable}")
    print(f"Regulatory authority verified: {evidence.regulatory_authority_replaced}")
    print(
        "PASS records require real local artifact bytes, matching SHA-256 "
        "and the qualified semantic schema"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
