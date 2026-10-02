"""Integration tests for LOT-27 generated regulatory compatibility matrix."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from pyaccountingkit.integrations.regulatory_framework import (
    RegulatoryCapabilityCode as Code,
)
from pyaccountingkit.integrations.regulatory_framework import (
    RegulatoryCapabilityStatus as Status,
)
from pyaccountingkit.integrations.regulatory_framework import (
    baseline_profiles,
    regulatory_compatibility_matrix_payload,
)

ROOT = Path(__file__).resolve().parents[2]


def test_matrix_is_capability_scoped_and_never_global_supported_boolean() -> None:
    payload = regulatory_compatibility_matrix_payload(
        "0.7.0a3",
        baseline_profiles("0.7.0a3"),
    )
    assert payload["qualification_model"] == "capability-scoped/v1"
    profiles = payload["regulatory_frameworks"]
    assert isinstance(profiles, list)
    assert len(profiles) == 5
    for profile in profiles:
        assert isinstance(profile, dict)
        assert profile["qualification_scope"] == "CAPABILITY_SCOPED"
        assert "supported" not in profile
        assert isinstance(profile["capabilities"], dict)


def test_ebnl_and_ohada_relation_capabilities_are_promoted_narrowly() -> None:
    profiles = {profile.standard_ref: profile for profile in baseline_profiles("0.7.0a3")}
    assert profiles["ohada-ebnl:2023"].production_qualified_capabilities == (
        Code.STRUCTURE,
        Code.RELATIONS,
        Code.SNAPSHOTS,
    )
    assert profiles["cemac-pcemf:2010"].production_qualified_capabilities == (Code.RELATIONS,)

    pcemf = profiles["cemac-pcemf:2010"]
    assert pcemf.qualification_for(Code.STRUCTURE).status is Status.NOT_ASSERTED
    assert pcemf.qualification_for(Code.CROSSWALKS).status is Status.NOT_ASSERTED

    ebnl = profiles["ohada-ebnl:2023"]
    assert ebnl.qualification_for(Code.CROSSWALKS).status is Status.REVIEW_REQUIRED
    assert ebnl.qualification_for(Code.NEGATIVE_CONSTRAINTS).status is Status.FORBIDDEN_INFERENCE


def test_nonprofit_effective_plan_and_snapshots_are_production_qualified() -> None:
    profiles = {profile.standard_ref: profile for profile in baseline_profiles("0.7.0a3")}
    assert profiles["fr-nonprofit:2026"].production_qualified_capabilities == (
        Code.EFFECTIVE_PLAN,
        Code.SNAPSHOTS,
    )


def test_generated_matrix_is_committed_deterministically() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_regulatory_compatibility_matrix.py",
            "--check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "REGULATORY_COMPATIBILITY_MATRIX.json: OK" in result.stdout


def test_committed_matrix_preserves_nonprofit_review_required_mapping() -> None:
    payload = json.loads(
        (ROOT / "REGULATORY_COMPATIBILITY_MATRIX.json").read_text(encoding="utf-8")
    )
    profiles = {profile["standard_ref"]: profile for profile in payload["regulatory_frameworks"]}
    mapping = profiles["fr-nonprofit:2026"]["capabilities"]["REPORTING_ACCOUNT_MAPPINGS"]
    assert mapping["status"] == Status.REVIEW_REQUIRED.value
    assert mapping["executable"] is False
    assert mapping["human_review_required"] is True
