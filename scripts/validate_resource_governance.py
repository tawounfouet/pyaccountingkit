#!/usr/bin/env python3
"""Validate repository resource provenance and rights-governance contracts."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "RESOURCE_GOVERNANCE.json"
RESOURCES = ROOT / "resources"

ALLOWED_RIGHTS_STATUS = {
    "NO_SEPARATE_LICENSE_DECLARATION",
    "MIXED_OR_UNASSERTED_REVIEW_REQUIRED",
}
ALLOWED_REDISTRIBUTION_STATUS = {
    "REPOSITORY_REFERENCE_ONLY",
    "REVIEW_REQUIRED_BEFORE_EXTERNAL_REPACKAGING",
}


class ResourceGovernanceError(RuntimeError):
    """Raised when resource governance cannot be evaluated safely."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ResourceGovernanceError(f"invalid JSON in {path}: {exc}") from exc


def _git_tree_sha(relative_path: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", f"HEAD:{relative_path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "git tree lookup failed"
        raise ResourceGovernanceError(f"{relative_path}: {detail}")
    return completed.stdout.strip()


def _resource_directories(root: Path = RESOURCES) -> set[str]:
    if not root.is_dir():
        raise ResourceGovernanceError("resources directory is missing")
    return {
        item.relative_to(ROOT).as_posix()
        for item in root.iterdir()
        if item.is_dir() and not item.name.startswith(".")
    }


def _required_policy_violations(policy: object) -> list[str]:
    if not isinstance(policy, dict):
        return ["RESOURCE_GOVERNANCE.json.policy must be an object"]

    expected = {
        "project_license": "MIT",
        "project_license_file": "LICENSE",
        "third_party_notice_file": "THIRD_PARTY_NOTICES.md",
        "package_inclusion": "FORBIDDEN",
        "runtime_dependency": "FORBIDDEN",
        "production_or_confidential_data": "FORBIDDEN",
    }
    violations: list[str] = []
    for key, value in expected.items():
        if policy.get(key) != value:
            violations.append(f"policy.{key} must be {value!r}")

    requirements = policy.get("resource_change_requires")
    required_items = {
        "provenance_review",
        "rights_status_review",
        "bundle_fingerprint_update",
        "manifest_or_source_checksum_review",
        "ci_governance_gate",
    }
    if not isinstance(requirements, list) or not required_items.issubset(set(requirements)):
        violations.append("policy.resource_change_requires is incomplete")
    return violations


def validate_registry_data(
    data: object,
    *,
    resource_directories: set[str],
    tree_lookup: Callable[[str], str],
    root: Path = ROOT,
) -> list[str]:
    """Return governance violations for one resource registry payload."""
    if not isinstance(data, dict):
        return ["RESOURCE_GOVERNANCE.json must contain an object"]
    violations: list[str] = []

    if data.get("schema_version") != "1":
        violations.append("resource governance schema_version must be '1'")
    violations.extend(_required_policy_violations(data.get("policy")))

    bundles = data.get("bundles")
    if not isinstance(bundles, list):
        return violations + ["RESOURCE_GOVERNANCE.json.bundles must be a list"]

    seen_paths: set[str] = set()
    seen_ids: set[str] = set()
    for index, bundle in enumerate(bundles):
        label = f"bundles[{index}]"
        if not isinstance(bundle, dict):
            violations.append(f"{label} must be an object")
            continue

        bundle_id = bundle.get("id")
        path = bundle.get("path")
        if not isinstance(bundle_id, str) or not bundle_id:
            violations.append(f"{label}.id must be a non-empty string")
        elif bundle_id in seen_ids:
            violations.append(f"duplicate resource bundle id: {bundle_id}")
        else:
            seen_ids.add(bundle_id)

        if not isinstance(path, str) or path not in resource_directories:
            violations.append(f"{label}.path is not a governed resource directory: {path!r}")
            continue
        if path in seen_paths:
            violations.append(f"duplicate resource bundle path: {path}")
            continue
        seen_paths.add(path)

        if bundle.get("package_inclusion") is not False:
            violations.append(f"{path}: package_inclusion must be false")
        if bundle.get("runtime_dependency") is not False:
            violations.append(f"{path}: runtime_dependency must be false")
        if bundle.get("mutable_in_place") is not False:
            violations.append(f"{path}: mutable_in_place must be false")

        rights_status = bundle.get("rights_status")
        if rights_status not in ALLOWED_RIGHTS_STATUS:
            violations.append(f"{path}: unsupported rights_status {rights_status!r}")

        redistribution = bundle.get("redistribution_status")
        if redistribution not in ALLOWED_REDISTRIBUTION_STATUS:
            violations.append(f"{path}: unsupported redistribution_status {redistribution!r}")

        contains_third_party = bundle.get("contains_third_party_sources")
        if not isinstance(contains_third_party, bool):
            violations.append(f"{path}: contains_third_party_sources must be boolean")
        if contains_third_party and rights_status != "MIXED_OR_UNASSERTED_REVIEW_REQUIRED":
            violations.append(
                f"{path}: third-party source bundle must remain rights-review-required"
            )

        expected_tree = bundle.get("tree_sha")
        if not isinstance(expected_tree, str) or len(expected_tree) != 40:
            violations.append(f"{path}: tree_sha must be a 40-character Git object id")
        else:
            try:
                actual_tree = tree_lookup(path)
            except ResourceGovernanceError as exc:
                violations.append(str(exc))
            else:
                if actual_tree != expected_tree:
                    violations.append(
                        f"{path}: tree SHA drifted: {actual_tree} != {expected_tree}"
                    )

        manifest_path = bundle.get("manifest_path")
        if not isinstance(manifest_path, str):
            violations.append(f"{path}: manifest_path must be declared")
            continue
        manifest_file = root / manifest_path
        if not manifest_file.is_file():
            violations.append(f"{path}: manifest missing: {manifest_path}")
            continue

        try:
            manifest = _load_json(manifest_file)
        except ResourceGovernanceError as exc:
            violations.append(str(exc))
            continue
        if not isinstance(manifest, dict):
            violations.append(f"{manifest_path}: manifest must be a JSON object")
            continue

        expected_project = bundle.get("manifest_project")
        expected_version = bundle.get("manifest_version")
        if manifest.get("project") != expected_project:
            violations.append(
                f"{manifest_path}: project {manifest.get('project')!r} "
                f"!= {expected_project!r}"
            )
        if manifest.get("version") != expected_version:
            violations.append(
                f"{manifest_path}: version {manifest.get('version')!r} "
                f"!= {expected_version!r}"
            )

    missing = sorted(resource_directories - seen_paths)
    extra = sorted(seen_paths - resource_directories)
    if missing:
        violations.append(f"resource directories missing governance entries: {missing}")
    if extra:
        violations.append(f"governance entries without resource directories: {extra}")

    for required_file in ("LICENSE", "THIRD_PARTY_NOTICES.md", "resources/README.md"):
        if not (root / required_file).is_file():
            violations.append(f"required governance file missing: {required_file}")

    return violations


def resource_governance_violations() -> list[str]:
    """Validate the checked-out repository resource-governance state."""
    if not REGISTRY.is_file():
        return ["RESOURCE_GOVERNANCE.json is missing"]
    try:
        data = _load_json(REGISTRY)
        directories = _resource_directories()
    except ResourceGovernanceError as exc:
        return [str(exc)]
    return validate_registry_data(
        data,
        resource_directories=directories,
        tree_lookup=_git_tree_sha,
    )


def main() -> int:
    """CLI entry point."""
    violations = resource_governance_violations()
    if violations:
        print("Resource governance validation: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    data = _load_json(REGISTRY)
    bundles = data["bundles"]
    print("Resource governance validation: PASS")
    print(f"Governed resource bundles: {len(bundles)}")
    for bundle in bundles:
        print(
            f"- {bundle['id']}: {bundle['manifest_version']} "
            f"[{bundle['rights_status']}]"
        )
    print("Wheel inclusion: FORBIDDEN")
    print("Runtime dependency: FORBIDDEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
