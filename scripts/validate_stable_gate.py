#!/usr/bin/env python3
"""Validate the fail-closed G5 stable-release contract for PyAccountingKit 0.7.0."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NON_EXECUTABLE = {
    "NOT_ASSERTED",
    "DISCOVERED",
    "INGESTIBLE",
    "VALIDATED",
    "CANDIDATE",
    "REVIEW_REQUIRED",
    "FORBIDDEN_INFERENCE",
}


class StableGateError(RuntimeError):
    """Raised when stable-gate source data cannot be read safely."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StableGateError(f"cannot read {path}: {exc}") from exc


def _project_version(root: Path) -> str:
    try:
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise StableGateError(f"cannot read pyproject.toml: {exc}") from exc
    return str(data["project"]["version"])


def _profile_map(matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_profiles = matrix.get("regulatory_frameworks")
    if not isinstance(raw_profiles, list):
        return {}
    return {
        str(item["standard_ref"]): item
        for item in raw_profiles
        if isinstance(item, dict) and isinstance(item.get("standard_ref"), str)
    }


def _capability_status(
    profiles: dict[str, dict[str, Any]],
    standard_ref: str,
    capability: str,
) -> str | None:
    profile = profiles.get(standard_ref)
    if profile is None:
        return None
    capabilities = profile.get("capabilities")
    if not isinstance(capabilities, dict):
        return None
    record = capabilities.get(capability)
    if not isinstance(record, dict):
        return None
    status = record.get("status")
    return status if isinstance(status, str) else None


def stable_gate_violations(*, root: Path = ROOT, target_version: str = "0.7.0") -> list[str]:
    """Return every G5 violation that must block stable promotion."""
    violations: list[str] = []

    try:
        version = _project_version(root)
    except StableGateError as exc:
        return [str(exc)]
    if version != target_version:
        violations.append(
            f"project version must be exact stable target {target_version}; found {version}"
        )

    status_path = root / "docs/audits/LOT_00_REMEDIATION_STATUS.json"
    try:
        status = _load_json(status_path)
    except StableGateError as exc:
        return violations + [str(exc)]
    if not isinstance(status, dict):
        return violations + ["LOT-00 status must be a JSON object"]

    if status.get("overall_status") != "COMPLETE":
        violations.append("LOT-00 final qualification must be COMPLETE before G5")

    blockers = status.get("blockers")
    if not isinstance(blockers, list):
        violations.append("LOT-00 blocker registry must be a list")
    else:
        open_blockers = [
            str(item.get("id"))
            for item in blockers
            if isinstance(item, dict) and item.get("status") == "OPEN"
        ]
        if open_blockers:
            violations.append(f"G5 requires 0 BLOCKER; open blockers: {', '.join(open_blockers)}")

    sublots = status.get("sublots")
    if not isinstance(sublots, list):
        violations.append("LOT-00 sublot registry is invalid")
    else:
        lot009 = next(
            (item for item in sublots if isinstance(item, dict) and item.get("id") == "LOT-00.9"),
            None,
        )
        if not isinstance(lot009, dict) or lot009.get("status") != "COMPLETE":
            violations.append("LOT-00.9 must be COMPLETE before stable promotion")

    external = status.get("external_controls")
    main_branch = external.get("main_branch") if isinstance(external, dict) else None
    if not isinstance(main_branch, dict) or main_branch.get("observed_protected") is not True:
        violations.append("main branch protection must be observed true before G5")

    docs = {
        "README.md": f"PyAccountingKit **{target_version}**",
        "CHANGELOG.md": f"## [{target_version}]",
        "docs/plans/LOT-27_REGULATORY_PRODUCTION_QUALIFICATION_PLAN.md": (
            f"**Current slice:** `{target_version}`"
        ),
        "docs/plans/RELEASE_0.7.0_STABLE_PROMOTION_PLAN.md": "Migration impact: none",
    }
    for relative, marker in docs.items():
        path = root / relative
        if not path.is_file():
            violations.append(f"required G5 document missing: {relative}")
        elif marker not in path.read_text(encoding="utf-8"):
            violations.append(f"{relative}: missing stable marker {marker!r}")

    rc_audit = root / "docs/audits/2026-10-03_LOT_27_RC1_QUALIFICATION.md"
    if not rc_audit.is_file():
        violations.append("LOT-27 RC1 qualification audit is missing")

    g5_external_path = root / "docs/audits/G5_EXTERNAL_CONTROLS.json"
    try:
        g5_external = _load_json(g5_external_path)
    except StableGateError as exc:
        violations.append(str(exc))
    else:
        if not isinstance(g5_external, dict):
            violations.append("G5 external controls must be a JSON object")
        else:
            controls = g5_external.get("controls")
            immutable = controls.get("immutable_releases") if isinstance(controls, dict) else None
            if not isinstance(immutable, dict):
                violations.append("G5 immutable-releases control is missing")
            else:
                if immutable.get("required") is not True:
                    violations.append("GitHub release immutability must remain required")
                if immutable.get("observed_enabled") is not True:
                    violations.append(
                        "GitHub release immutability must be observed enabled before G5"
                    )
                if immutable.get("status") != "COMPLETE":
                    violations.append("G5 immutable-releases control must be COMPLETE")
            external_blockers = g5_external.get("blockers")
            if not isinstance(external_blockers, list):
                violations.append("G5 external blocker registry must be a list")
            else:
                open_external = [
                    str(item.get("id"))
                    for item in external_blockers
                    if isinstance(item, dict) and item.get("status") == "OPEN"
                ]
                if open_external:
                    violations.append(
                        f"G5 external controls remain open: {', '.join(open_external)}"
                    )

    manifest_names = (
        "PUBLIC_API_MANIFEST.json",
        "PUBLIC_ERROR_CODES.json",
        "ADAPTER_CONTRACT_MANIFEST.json",
        "REGULATORY_COMPATIBILITY_MATRIX.json",
        "SNAPSHOT_SCHEMA_MANIFEST.json",
    )
    manifests: dict[str, dict[str, Any]] = {}
    for relative in manifest_names:
        try:
            payload = _load_json(root / relative)
        except StableGateError as exc:
            violations.append(str(exc))
            continue
        if not isinstance(payload, dict):
            violations.append(f"{relative}: manifest must be a JSON object")
            continue
        manifests[relative] = payload
        if payload.get("version") != target_version:
            violations.append(
                f"{relative}: version must be {target_version}; found {payload.get('version')}"
            )

    public_api = manifests.get("PUBLIC_API_MANIFEST.json")
    if isinstance(public_api, dict):
        public = public_api.get("public_api")
        stability = public.get("stability") if isinstance(public, dict) else None
        if stability != "pre-1.0-stable-release":
            violations.append(
                "PUBLIC_API_MANIFEST.json: stable promotion requires pre-1.0-stable-release"
            )

    matrix = manifests.get("REGULATORY_COMPATIBILITY_MATRIX.json")
    if isinstance(matrix, dict):
        profiles = _profile_map(matrix)
        expected_refs = {
            "cemac-pcemf:2010",
            "fr-nonprofit:2026",
            "fr-pcg:2026",
            "ohada-ebnl:2023",
            "ohada-syscohada:2017",
        }
        if set(profiles) != expected_refs:
            violations.append("stable regulatory matrix must preserve the five reviewed profiles")

        expected_statuses = {
            ("fr-pcg:2026", "REPORTING_STRUCTURE"): "PRODUCTION_QUALIFIED",
            ("fr-pcg:2026", "REPORTING_ACCOUNT_MAPPINGS"): "REVIEW_REQUIRED",
            ("fr-nonprofit:2026", "REPORTING_STRUCTURE"): "PRODUCTION_QUALIFIED",
            ("fr-nonprofit:2026", "REPORTING_ACCOUNT_MAPPINGS"): "REVIEW_REQUIRED",
            ("ohada-syscohada:2017", "REPORTING_STRUCTURE"): "PRODUCTION_QUALIFIED",
            ("ohada-syscohada:2017", "REPORTING_ACCOUNT_MAPPINGS"): "REVIEW_REQUIRED",
            ("ohada-ebnl:2023", "REPORTING_STRUCTURE"): "DISCOVERED",
            ("ohada-ebnl:2023", "CROSSWALKS"): "REVIEW_REQUIRED",
            ("cemac-pcemf:2010", "CROSSWALKS"): "NOT_ASSERTED",
        }
        for (standard_ref, capability), expected in expected_statuses.items():
            actual = _capability_status(profiles, standard_ref, capability)
            if actual != expected:
                violations.append(
                    f"{standard_ref}/{capability}: stable gate expected {expected}, found {actual}"
                )

        for standard_ref, profile in profiles.items():
            if "supported" in profile or "SUPPORTED" in profile:
                violations.append(f"{standard_ref}: global support flag is forbidden")
            capabilities = profile.get("capabilities")
            if not isinstance(capabilities, dict):
                continue
            for code, raw in capabilities.items():
                if not isinstance(raw, dict):
                    violations.append(f"{standard_ref}/{code}: invalid qualification object")
                    continue
                status_code = raw.get("status")
                if status_code in NON_EXECUTABLE and raw.get("executable") is not False:
                    violations.append(
                        f"{standard_ref}/{code}: {status_code} must remain non-executable"
                    )
                if raw.get("auto_inference_allowed") is True:
                    violations.append(
                        f"{standard_ref}/{code}: automatic semantic inference remains forbidden"
                    )

    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-version", default="0.7.0")
    args = parser.parse_args(argv)

    violations = stable_gate_violations(target_version=args.target_version)
    if violations:
        print("G5 stable gate: BLOCKED", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 2

    print("G5 stable gate: PASS")
    print(f"Stable target: {args.target_version}")
    print("Open blockers: 0")
    print("Regulatory capability set: frozen from qualified 0.7.0rc1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
