"""LOT-26 tests for deterministic CFA FRA cutover artifact generation."""

from __future__ import annotations

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    CutoverArtifactGenerationError,
    LegacyIdentityLink,
    LegacyIdentityMap,
    MigrationRouting,
    RegulatoryAuthorityObservation,
    RegulatoryAuthorityResolution,
    generate_legacy_identity_artifact,
    generate_regulatory_authority_artifact,
)


def _identities() -> LegacyIdentityMap:
    return LegacyIdentityMap(
        (
            LegacyIdentityLink(
                legacy_type="JournalEntry",
                legacy_id="legacy-2",
                target_type="JournalEntry",
                target_id="target-2",
            ),
            LegacyIdentityLink(
                legacy_type="JournalEntry",
                legacy_id="legacy-1",
                target_type="JournalEntry",
                target_id="target-1",
                source_checksum="sha256:" + ("a" * 64),
            ),
        )
    )


def _authority_observation(
    *,
    routing: MigrationRouting | None = None,
    local_authority: bool = False,
) -> RegulatoryAuthorityObservation:
    return RegulatoryAuthorityObservation(
        provider_name="PyAccountingKit",
        provider_version="0.6.0b17",
        routing=routing if routing is not None else MigrationRouting.target_only(),
        local_framework_account_authority=local_authority,
        local_seed_commands_authoritative=False,
        effective_plan_delegated=True,
        resolutions=(
            RegulatoryAuthorityResolution(
                standard_id="SYSCOHADA",
                edition="2017",
                reference_key="101000",
                target_reference_id="reference-101000",
            ),
        ),
    )


def test_identity_generation_is_complete_and_deterministic() -> None:
    generated = generate_legacy_identity_artifact(
        consumer="CFA FRA",
        generated_at="2026-09-30T13:00:00Z",
        identities=_identities(),
        expected_legacy_records=2,
    )

    mappings = generated.payload["mappings"]
    assert [mapping["legacy_id"] for mapping in mappings] == [
        "legacy-1",
        "legacy-2",
    ]
    assert generated.payload["summary"] == {
        "total_legacy_records": 2,
        "mapped_records": 2,
        "unresolved_records": 0,
    }


def test_identity_generation_rejects_incomplete_snapshot() -> None:
    with pytest.raises(CutoverArtifactGenerationError, match="snapshot is incomplete"):
        generate_legacy_identity_artifact(
            consumer="CFA FRA",
            generated_at="2026-09-30T13:00:00Z",
            identities=_identities(),
            expected_legacy_records=3,
        )


def test_regulatory_generation_requires_target_only_cutover() -> None:
    with pytest.raises(CutoverArtifactGenerationError, match="target-only"):
        generate_regulatory_authority_artifact(
            consumer="CFA FRA",
            observed_at="2026-09-30T13:00:00Z",
            observation=_authority_observation(routing=MigrationRouting()),
        )


def test_regulatory_generation_rejects_retained_local_authority() -> None:
    with pytest.raises(CutoverArtifactGenerationError, match="must be disabled"):
        generate_regulatory_authority_artifact(
            consumer="CFA FRA",
            observed_at="2026-09-30T13:00:00Z",
            observation=_authority_observation(local_authority=True),
        )


def test_regulatory_generation_materializes_schema_valid_payload() -> None:
    generated = generate_regulatory_authority_artifact(
        consumer="CFA FRA",
        observed_at="2026-09-30T13:00:00Z",
        observation=_authority_observation(),
    )

    assert generated.payload["routing_profile"] == "target_only"
    assert generated.payload["provider"] == {
        "name": "PyAccountingKit",
        "version": "0.6.0b17",
    }
    assert generated.payload["sample_resolutions"] == [
        {
            "standard_id": "SYSCOHADA",
            "edition": "2017",
            "reference_key": "101000",
            "target_reference_id": "reference-101000",
        }
    ]
