#!/usr/bin/env python3
"""Validate the REM-10 remediation registry before 0.7.0rc2 qualification."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "audits" / "REMEDIATION_2026_10_STATUS.json"
ALLOWED_FINDING_STATUSES = frozenset({"FIXED_UNVERIFIED", "VERIFIED"})
EXPECTED_FINDINGS = frozenset(
    {f"F{index:02d}" for index in range(1, 28)}
    | {"A01", "A02", "A03"}
)
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _project_version(root: Path) -> str:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _load_registry(root: Path) -> dict[str, Any]:
    payload = json.loads(
        (root / "docs" / "audits" / "REMEDIATION_2026_10_STATUS.json").read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(payload, dict):
        raise ValueError("remediation registry must be a JSON object")
    return payload


def remediation_release_violations(*, root: Path = ROOT) -> list[str]:
    """Return every REM-10 condition that must block the RC candidate."""

    violations: list[str] = []
    try:
        version = _project_version(root)
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        return [f"cannot read project version: {exc}"]

    try:
        registry = _load_registry(root)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot read remediation registry: {exc}"]

    if registry.get("package_version") != version:
        violations.append(
            "remediation registry package_version must match pyproject version "
            f"({registry.get('package_version')!r} != {version!r})"
        )

    remediation = registry.get("remediation")
    if not isinstance(remediation, dict):
        return violations + ["remediation registry requires a remediation object"]
    if remediation.get("current_phase") != "REM-10":
        violations.append("current remediation phase must be REM-10")

    rem09 = remediation.get("rem09")
    if not isinstance(rem09, dict) or rem09.get("implementation_status") != "COMPLETE":
        violations.append("REM-09 implementation must be COMPLETE before REM-10")

    lots = registry.get("lots")
    if not isinstance(lots, dict):
        violations.append("remediation registry requires a lots object")
    else:
        rem10 = lots.get("REM-10")
        if not isinstance(rem10, dict):
            violations.append("REM-10 lot is missing")
        elif rem10.get("status") not in {"QUALIFYING", "DONE"}:
            violations.append("REM-10 status must be QUALIFYING or DONE")

    findings = registry.get("findings")
    if not isinstance(findings, list):
        return violations + ["remediation registry requires a findings array"]

    by_id: dict[str, dict[str, Any]] = {}
    for raw in findings:
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
            violations.append("every finding must be a JSON object with a string id")
            continue
        finding_id = str(raw["id"])
        if finding_id in by_id:
            violations.append(f"duplicate finding id: {finding_id}")
            continue
        by_id[finding_id] = raw

    actual_ids = frozenset(by_id)
    missing = sorted(EXPECTED_FINDINGS - actual_ids)
    extra = sorted(actual_ids - EXPECTED_FINDINGS)
    if missing:
        violations.append(f"missing findings: {', '.join(missing)}")
    if extra:
        violations.append(f"unexpected findings: {', '.join(extra)}")
    if len(findings) != 30:
        violations.append(f"expected exactly 30 findings, found {len(findings)}")

    for finding_id in sorted(EXPECTED_FINDINGS & actual_ids):
        finding = by_id[finding_id]
        status = finding.get("status")
        if status not in ALLOWED_FINDING_STATUSES:
            violations.append(
                f"{finding_id}: status must be FIXED_UNVERIFIED or VERIFIED; found {status!r}"
            )

        if finding.get("release_scope") != "IN_SCOPE":
            violations.append(
                f"{finding_id}: release_scope must be IN_SCOPE; found "
                f"{finding.get('release_scope')!r}"
            )

        if finding.get("qualification_lot") != "REM-10":
            violations.append(f"{finding_id}: qualification_lot must be REM-10")

        fix_sha = finding.get("fix_sha")
        if not isinstance(fix_sha, str) or SHA_PATTERN.fullmatch(fix_sha) is None:
            violations.append(f"{finding_id}: fix_sha must be a lowercase 40-hex SHA")

        corrective_tests = finding.get("corrective_tests")
        if not isinstance(corrective_tests, list) or not corrective_tests:
            violations.append(f"{finding_id}: corrective_tests must be non-empty")
        else:
            for test_ref in corrective_tests:
                if not isinstance(test_ref, str) or not test_ref:
                    violations.append(f"{finding_id}: invalid corrective test reference")
                    continue
                test_path = test_ref.split("::", 1)[0]
                if not (root / test_path).is_file():
                    violations.append(
                        f"{finding_id}: corrective test path does not exist: {test_path}"
                    )

        evidence = finding.get("qualification_evidence")
        if not isinstance(evidence, list) or not evidence:
            violations.append(f"{finding_id}: qualification_evidence must be non-empty")

    a01 = by_id.get("A01")
    if isinstance(a01, dict) and a01.get("release_scope") != "IN_SCOPE":
        violations.append("A01 must be explicitly IN_SCOPE for 0.7.0rc2")

    return violations


def main() -> int:
    violations = remediation_release_violations()
    if violations:
        print("REM-10 remediation gate: BLOCKED", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 2

    print("REM-10 remediation gate: PASS")
    print(f"Candidate version: {_project_version(ROOT)}")
    print("Findings: 30")
    print("Open findings: 0")
    print("Allowed states: FIXED_UNVERIFIED / VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
