#!/usr/bin/env python3
"""Validate the executable LOT-27 regulatory gate without broad support inference."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "REGULATORY_COMPATIBILITY_MATRIX.json"

_NON_EXECUTABLE = {
    "NOT_ASSERTED",
    "DISCOVERED",
    "INGESTIBLE",
    "VALIDATED",
    "CANDIDATE",
    "REVIEW_REQUIRED",
    "FORBIDDEN_INFERENCE",
}


def _capability(profile: dict[str, Any], code: str) -> dict[str, Any] | None:
    capabilities = profile.get("capabilities")
    if not isinstance(capabilities, dict):
        return None
    raw = capabilities.get(code)
    return raw if isinstance(raw, dict) else None


def _expect_status(
    violations: list[str],
    profiles: dict[str, dict[str, Any]],
    standard_ref: str,
    capability: str,
    expected: str,
) -> None:
    profile = profiles.get(standard_ref)
    if profile is None:
        violations.append(f"missing regulatory profile: {standard_ref}")
        return
    record = _capability(profile, capability)
    if record is None:
        violations.append(f"{standard_ref}/{capability}: qualification missing")
        return
    if record.get("status") != expected:
        violations.append(
            f"{standard_ref}/{capability}: expected {expected}, found {record.get('status')}"
        )


def validate_payload(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    raw_profiles = payload.get("regulatory_frameworks")
    if not isinstance(raw_profiles, list):
        return ["regulatory_frameworks must be a list"]

    profiles: dict[str, dict[str, Any]] = {}
    for raw_profile in raw_profiles:
        if not isinstance(raw_profile, dict):
            violations.append("regulatory profile must be an object")
            continue
        standard_ref = raw_profile.get("standard_ref")
        if not isinstance(standard_ref, str) or not standard_ref:
            violations.append("regulatory profile requires standard_ref")
            continue
        profiles[standard_ref] = raw_profile

        if "supported" in raw_profile or "SUPPORTED" in raw_profile:
            violations.append(f"{standard_ref}: global supported flag is forbidden")

        capabilities = raw_profile.get("capabilities")
        if not isinstance(capabilities, dict):
            violations.append(f"{standard_ref}: capabilities must be an object")
            continue
        for code, raw_record in capabilities.items():
            if not isinstance(raw_record, dict):
                violations.append(f"{standard_ref}/{code}: qualification must be an object")
                continue
            status = raw_record.get("status")
            executable = raw_record.get("executable")
            human_review = raw_record.get("human_review_required")
            auto_inference = raw_record.get("auto_inference_allowed")

            if status in _NON_EXECUTABLE and executable is not False:
                violations.append(
                    f"{standard_ref}/{code}: {status} capability must remain non-executable"
                )
            if human_review is True and executable is not False:
                violations.append(
                    f"{standard_ref}/{code}: human-review capability must remain non-executable"
                )
            if auto_inference is True:
                violations.append(
                    f"{standard_ref}/{code}: automatic semantic inference is not qualified"
                )
            if status == "PRODUCTION_QUALIFIED":
                for evidence_key in ("evidence_refs", "golden_refs"):
                    evidence = raw_record.get(evidence_key)
                    if not isinstance(evidence, list) or not evidence:
                        violations.append(
                            f"{standard_ref}/{code}: production qualification lacks {evidence_key}"
                        )
                if executable is not True:
                    violations.append(
                        f"{standard_ref}/{code}: production qualification must be executable"
                    )

    expected_refs = {
        "cemac-pcemf:2010",
        "fr-nonprofit:2026",
        "fr-pcg:2026",
        "ohada-ebnl:2023",
        "ohada-syscohada:2017",
    }
    if set(profiles) != expected_refs:
        violations.append("LOT-27 requires exactly the five reviewed regulatory profiles")

    for ref in ("fr-pcg:2026", "fr-nonprofit:2026", "ohada-syscohada:2017"):
        _expect_status(
            violations,
            profiles,
            ref,
            "REPORTING_STRUCTURE",
            "PRODUCTION_QUALIFIED",
        )
        _expect_status(
            violations,
            profiles,
            ref,
            "REPORTING_ACCOUNT_MAPPINGS",
            "REVIEW_REQUIRED",
        )

    _expect_status(
        violations,
        profiles,
        "ohada-ebnl:2023",
        "REPORTING_STRUCTURE",
        "DISCOVERED",
    )
    _expect_status(
        violations,
        profiles,
        "ohada-ebnl:2023",
        "CROSSWALKS",
        "REVIEW_REQUIRED",
    )
    _expect_status(
        violations,
        profiles,
        "ohada-ebnl:2023",
        "NEGATIVE_CONSTRAINTS",
        "FORBIDDEN_INFERENCE",
    )
    _expect_status(
        violations,
        profiles,
        "cemac-pcemf:2010",
        "CROSSWALKS",
        "NOT_ASSERTED",
    )
    _expect_status(
        violations,
        profiles,
        "cemac-pcemf:2010",
        "NEGATIVE_CONSTRAINTS",
        "FORBIDDEN_INFERENCE",
    )
    return violations


def main() -> int:
    try:
        payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Regulatory gate: FAIL: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print("Regulatory gate: FAIL: matrix must be a JSON object", file=sys.stderr)
        return 1

    violations = validate_payload(payload)
    if violations:
        print("Regulatory gate: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print("Regulatory gate: PASS")
    print("GR invariants: source-backed, review-preserving, inference-free")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
