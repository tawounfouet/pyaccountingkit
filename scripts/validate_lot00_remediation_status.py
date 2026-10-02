#!/usr/bin/env python3
"""Validate the machine-readable LOT-00 remediation closure record."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "docs" / "audits" / "LOT_00_REMEDIATION_STATUS.json"

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?$")
_EXPECTED_SUBLOTS = tuple(f"LOT-00.{index}" for index in range(1, 10))
_COMPLETED_SUBLOTS = set(_EXPECTED_SUBLOTS[:-1])
_REQUIRED_REPOSITORY_CONTROLS = {
    "architecture_gate",
    "manifest_coherence",
    "ci_contract",
    "security_workflow",
    "package_qualification",
    "release_hardening",
    "resource_governance",
}
_REQUIRED_STATUS_CHECKS = {
    "Canonical CI gate",
    "Dependency audit",
    "Static security analysis",
}


class Lot00QualificationError(RuntimeError):
    """Raised when the LOT-00 qualification record is invalid."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Lot00QualificationError(f"invalid JSON in {path}: {exc}") from exc


def validate_status_data(data: object, *, root: Path = ROOT) -> list[str]:
    """Return consistency violations for one LOT-00 remediation status payload."""
    if not isinstance(data, dict):
        return ["LOT-00 remediation status must be a JSON object"]

    violations: list[str] = []

    if data.get("schema_version") != "1":
        violations.append("schema_version must be '1'")
    if data.get("lot") != "LOT-00":
        violations.append("lot must be 'LOT-00'")
    if data.get("historical_target_version") != "0.0.1":
        violations.append("historical_target_version must remain '0.0.1'")

    version = data.get("qualified_repository_version")
    if not isinstance(version, str) or _VERSION_RE.fullmatch(version) is None:
        violations.append("qualified_repository_version must be a canonical prerelease/stable version")

    baseline = data.get("baseline_main")
    if not isinstance(baseline, dict):
        violations.append("baseline_main must be an object")
    else:
        sha = baseline.get("sha")
        if not isinstance(sha, str) or _SHA_RE.fullmatch(sha) is None:
            violations.append("baseline_main.sha must be a 40-character lowercase Git SHA")
        ci = baseline.get("ci")
        security = baseline.get("security")
        if not isinstance(ci, dict) or ci.get("status") != "PASS":
            violations.append("baseline_main.ci.status must be PASS")
        elif ci.get("canonical_ci_gate") != "PASS":
            violations.append("baseline_main.ci.canonical_ci_gate must be PASS")
        if not isinstance(security, dict) or security.get("status") != "PASS":
            violations.append("baseline_main.security.status must be PASS")
        else:
            if security.get("dependency_audit") != "PASS":
                violations.append("baseline_main.security.dependency_audit must be PASS")
            if security.get("static_security_analysis") != "PASS":
                violations.append("baseline_main.security.static_security_analysis must be PASS")

    sublots = data.get("sublots")
    if not isinstance(sublots, list):
        return violations + ["sublots must be a list"]

    by_id: dict[str, dict[str, Any]] = {}
    for item in sublots:
        if not isinstance(item, dict):
            violations.append("every sublot entry must be an object")
            continue
        sublot_id = item.get("id")
        if not isinstance(sublot_id, str):
            violations.append("every sublot entry must have a string id")
            continue
        if sublot_id in by_id:
            violations.append(f"duplicate sublot entry: {sublot_id}")
            continue
        by_id[sublot_id] = item

    if tuple(sorted(by_id)) != _EXPECTED_SUBLOTS:
        violations.append(
            f"sublots must cover exactly {list(_EXPECTED_SUBLOTS)!r}; found {sorted(by_id)!r}"
        )

    for sublot_id in sorted(_COMPLETED_SUBLOTS):
        item = by_id.get(sublot_id)
        if item is None:
            continue
        if item.get("status") != "COMPLETE":
            violations.append(f"{sublot_id} must remain COMPLETE")
        merge_sha = item.get("merge_sha")
        if not isinstance(merge_sha, str) or _SHA_RE.fullmatch(merge_sha) is None:
            violations.append(f"{sublot_id}.merge_sha must be a 40-character lowercase Git SHA")
        evidence = item.get("evidence_files")
        if not isinstance(evidence, list):
            violations.append(f"{sublot_id}.evidence_files must be a list")
        else:
            for relative in evidence:
                if not isinstance(relative, str) or not relative:
                    violations.append(f"{sublot_id}: invalid evidence file path")
                    continue
                if not (root / relative).is_file():
                    violations.append(f"{sublot_id}: evidence file missing: {relative}")

    final_lot = by_id.get("LOT-00.9")
    if final_lot is not None and final_lot.get("status") not in {
        "COMPLETE",
        "BLOCKED_EXTERNAL_CONTROL",
    }:
        violations.append("LOT-00.9 status must be COMPLETE or BLOCKED_EXTERNAL_CONTROL")

    controls = data.get("repository_controls")
    if not isinstance(controls, dict):
        violations.append("repository_controls must be an object")
    else:
        missing_controls = sorted(_REQUIRED_REPOSITORY_CONTROLS - set(controls))
        if missing_controls:
            violations.append(f"repository_controls missing: {missing_controls}")
        for name in sorted(_REQUIRED_REPOSITORY_CONTROLS & set(controls)):
            if controls.get(name) != "PASS":
                violations.append(f"repository_controls.{name} must be PASS")

    external = data.get("external_controls")
    main_branch: dict[str, Any] | None = None
    if not isinstance(external, dict):
        violations.append("external_controls must be an object")
    else:
        raw_main = external.get("main_branch")
        if not isinstance(raw_main, dict):
            violations.append("external_controls.main_branch must be an object")
        else:
            main_branch = raw_main
            if raw_main.get("branch") != "main":
                violations.append("external_controls.main_branch.branch must be 'main'")
            if raw_main.get("required_protection") is not True:
                violations.append("main branch protection must remain required")
            checks = raw_main.get("required_status_checks")
            if not isinstance(checks, list) or not _REQUIRED_STATUS_CHECKS.issubset(set(checks)):
                violations.append("main branch required_status_checks are incomplete")
            if raw_main.get("required_force_push_block") is not True:
                violations.append("main branch force-push blocking must remain required")
            if raw_main.get("required_deletion_block") is not True:
                violations.append("main branch deletion blocking must remain required")

    blockers = data.get("blockers")
    if not isinstance(blockers, list):
        violations.append("blockers must be a list")
        blocker_ids: set[str] = set()
    else:
        blocker_ids = {
            str(item.get("id"))
            for item in blockers
            if isinstance(item, dict) and item.get("status") == "OPEN"
        }

    overall = data.get("overall_status")
    observed_protected = main_branch.get("observed_protected") if main_branch else None

    if observed_protected is False:
        if overall != "BLOCKED_EXTERNAL_CONTROL":
            violations.append(
                "overall_status cannot be COMPLETE while main protection is observed false"
            )
        if "MAIN_BRANCH_PROTECTION_UNENFORCED" not in blocker_ids:
            violations.append("missing open MAIN_BRANCH_PROTECTION_UNENFORCED blocker")
        if final_lot is not None and final_lot.get("status") != "BLOCKED_EXTERNAL_CONTROL":
            violations.append("LOT-00.9 must be BLOCKED_EXTERNAL_CONTROL while main is unprotected")
    elif observed_protected is True:
        if "MAIN_BRANCH_PROTECTION_UNENFORCED" in blocker_ids:
            violations.append("branch-protection blocker must be closed when protection is observed true")
        if overall == "COMPLETE" and final_lot is not None and final_lot.get("status") != "COMPLETE":
            violations.append("LOT-00.9 must be COMPLETE when overall_status is COMPLETE")
    else:
        violations.append("external_controls.main_branch.observed_protected must be boolean")

    claims = data.get("release_claims")
    if not isinstance(claims, dict):
        violations.append("release_claims must be an object")
    else:
        for name, value in claims.items():
            if value is not False:
                violations.append(f"release_claims.{name} must remain false for LOT-00.9")

    required_files = (
        "README.md",
        "CHANGELOG.md",
        "GOVERNANCE.md",
        "RESOURCE_GOVERNANCE.json",
        "THIRD_PARTY_NOTICES.md",
        ".github/CODEOWNERS",
        ".github/pull_request_template.md",
        ".github/workflows/ci.yml",
        ".github/workflows/security.yml",
        ".github/workflows/release.yml",
        "scripts/check_hygiene.sh",
        "scripts/validate_architecture.py",
        "scripts/validate_ci.py",
        "scripts/validate_resource_governance.py",
        "scripts/verify_package.py",
        "scripts/prepare_release.py",
        "scripts/qualify_release.py",
    )
    for relative in required_files:
        if not (root / relative).is_file():
            violations.append(f"required LOT-00 artifact missing: {relative}")

    return violations


def status_violations() -> list[str]:
    """Validate the checked-out remediation status record."""
    if not STATUS_FILE.is_file():
        return ["LOT_00_REMEDIATION_STATUS.json is missing"]
    try:
        data = _load_json(STATUS_FILE)
    except Lot00QualificationError as exc:
        return [str(exc)]
    return validate_status_data(data)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Return non-zero while LOT-00 final acceptance has an open blocker.",
    )
    args = parser.parse_args(argv)

    violations = status_violations()
    if violations:
        print("LOT-00 remediation status validation: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    data = _load_json(STATUS_FILE)
    overall = data["overall_status"]
    print("LOT-00 remediation status validation: PASS")
    print(f"Historical target: {data['historical_target_version']}")
    print(f"Qualified repository version: {data['qualified_repository_version']}")
    print(f"Overall status: {overall}")

    if args.require_complete and overall != "COMPLETE":
        print("LOT-00 final acceptance: BLOCKED", file=sys.stderr)
        for blocker in data["blockers"]:
            if blocker.get("status") == "OPEN":
                print(f"- {blocker['id']}: {blocker['resolution']}", file=sys.stderr)
        return 2

    if overall == "COMPLETE":
        print("LOT-00 final acceptance: COMPLETE")
    else:
        print("LOT-00 final acceptance: pending external control")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
