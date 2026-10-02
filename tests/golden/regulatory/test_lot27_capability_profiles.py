"""LOT-27 golden qualification against the bundled regulatory source corpus."""

from __future__ import annotations

import json
from pathlib import Path

from pyaccountingkit.integrations.regulatory_framework import (
    RegulatoryCapabilityCode as Code,
)
from pyaccountingkit.integrations.regulatory_framework import (
    RegulatoryCapabilityStatus as Status,
)
from pyaccountingkit.integrations.regulatory_framework import baseline_profiles

ROOT = Path(__file__).resolve().parents[3]
REGULATORY = ROOT / "resources" / "regulatory-accounting-data-framework"


def _profiles() -> dict[str, object]:
    return {profile.standard_ref: profile for profile in baseline_profiles("0.7.0b2")}


def test_baseline_profiles_cover_the_five_reviewed_standard_refs() -> None:
    assert set(_profiles()) == {
        "fr-pcg:2026",
        "fr-nonprofit:2026",
        "ohada-syscohada:2017",
        "ohada-ebnl:2023",
        "cemac-pcemf:2010",
    }


def test_pcg_and_syscohada_structure_and_snapshots_are_production_qualified() -> None:
    profiles = _profiles()
    for standard_ref in ("fr-pcg:2026", "ohada-syscohada:2017"):
        profile = profiles[standard_ref]
        structure = profile.qualification_for(Code.STRUCTURE)
        snapshots = profile.qualification_for(Code.SNAPSHOTS)
        assert structure is not None
        assert snapshots is not None
        assert structure.status is Status.PRODUCTION_QUALIFIED
        assert snapshots.status is Status.PRODUCTION_QUALIFIED
        assert structure.executable is True
        assert snapshots.executable is True


def test_nonprofit_effective_plan_stats_and_reporting_safety_match_source() -> None:
    manifest = json.loads((REGULATORY / "PROJECT_MANIFEST.json").read_text(encoding="utf-8"))
    stats = manifest["fr_nonprofit_2026"]["effective_plan"]
    assert stats == {
        "effective_accounts_or_groups": 901,
        "extension_additions": 73,
        "extension_overrides": 43,
        "inherited": 785,
    }

    reporting = json.loads(
        (REGULATORY / "datasets" / "reporting" / "nonprofit_2026_v3_reporting.json").read_text(
            encoding="utf-8"
        )
    )
    assert reporting["mapping_policy"]["account_hints_executable"] is False
    assert reporting["mapping_policy"]["human_validation_required"] is True

    profile = _profiles()["fr-nonprofit:2026"]
    mapping = profile.qualification_for(Code.REPORTING_ACCOUNT_MAPPINGS)
    assert mapping is not None
    assert mapping.status is Status.REVIEW_REQUIRED
    assert mapping.executable is False
    assert mapping.human_review_required is True

    effective = profile.qualification_for(Code.EFFECTIVE_PLAN)
    snapshots = profile.qualification_for(Code.SNAPSHOTS)
    overlays = profile.qualification_for(Code.OVERLAYS)
    assert effective is not None
    assert snapshots is not None
    assert overlays is not None
    assert effective.status is Status.PRODUCTION_QUALIFIED
    assert effective.executable is True
    assert snapshots.status is Status.PRODUCTION_QUALIFIED
    assert snapshots.executable is True
    assert overlays.status is Status.VALIDATED
    assert overlays.executable is False


def test_ohada_negative_constraints_forbid_false_inheritance() -> None:
    relations = json.loads(
        (
            REGULATORY / "datasets" / "relations" / "ohada_accounting_standard_relations.json"
        ).read_text(encoding="utf-8")
    )
    forbidden = {
        (
            item["subject_ref"],
            item["forbidden_relation_type"],
            item["target_ref"],
        )
        for item in relations["negative_constraints"]
    }
    assert (
        "cemac-pcemf:2010",
        "inherits",
        "ohada-syscohada:2017",
    ) in forbidden
    assert (
        "ohada-ebnl:2023",
        "inherits",
        "ohada-syscohada:2017",
    ) in forbidden

    profiles = _profiles()
    for standard_ref in ("cemac-pcemf:2010", "ohada-ebnl:2023"):
        qualification = profiles[standard_ref].qualification_for(Code.NEGATIVE_CONSTRAINTS)
        assert qualification is not None
        assert qualification.status is Status.FORBIDDEN_INFERENCE
        assert qualification.auto_inference_allowed is False
        assert qualification.executable is False


def test_ohada_ebnl_structure_relations_and_snapshots_are_production_qualified() -> None:
    profile = _profiles()["ohada-ebnl:2023"]
    assert profile.production_qualified_capabilities == (
        Code.STRUCTURE,
        Code.RELATIONS,
        Code.SNAPSHOTS,
    )
    for capability in (Code.STRUCTURE, Code.RELATIONS, Code.SNAPSHOTS):
        qualification = profile.qualification_for(capability)
        assert qualification is not None
        assert qualification.status is Status.PRODUCTION_QUALIFIED
        assert qualification.executable is True


def test_ohada_family_relations_are_production_qualified_without_enabling_inference() -> None:
    profiles = _profiles()
    for standard_ref in (
        "ohada-syscohada:2017",
        "ohada-ebnl:2023",
        "cemac-pcemf:2010",
    ):
        relation = profiles[standard_ref].qualification_for(Code.RELATIONS)
        assert relation is not None
        assert relation.status is Status.PRODUCTION_QUALIFIED
        assert relation.executable is True
        assert relation.auto_inference_allowed is False


def test_neutral_concepts_do_not_create_bindings() -> None:
    manifest = json.loads((REGULATORY / "PROJECT_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["ohada_family"]["concept_bindings"] == 0

    profiles = _profiles()
    ebnl_binding = profiles["ohada-ebnl:2023"].qualification_for(Code.CONCEPT_BINDINGS)
    pcemf_binding = profiles["cemac-pcemf:2010"].qualification_for(Code.CONCEPT_BINDINGS)
    assert ebnl_binding is not None
    assert pcemf_binding is not None
    assert ebnl_binding.status is Status.NOT_ASSERTED
    assert pcemf_binding.status is Status.NOT_ASSERTED


def test_ebnl_reporting_metadata_is_validated_without_mapping_or_export_promotion() -> None:
    profile = _profiles()["ohada-ebnl:2023"]

    structure = profile.qualification_for(Code.REPORTING_STRUCTURE)
    mappings = profile.qualification_for(Code.REPORTING_ACCOUNT_MAPPINGS)
    exports = profile.qualification_for(Code.EXPORTS)

    assert structure is not None
    assert structure.status is Status.VALIDATED
    assert structure.executable is False
    assert structure.golden_refs == (
        "tests/golden/regulatory/test_ebnl_reporting_registry.py",
    )

    assert mappings is not None
    assert mappings.status is Status.NOT_ASSERTED
    assert mappings.executable is False
    assert mappings.human_review_required is True

    assert exports is not None
    assert exports.status is Status.NOT_ASSERTED
    assert exports.executable is False
