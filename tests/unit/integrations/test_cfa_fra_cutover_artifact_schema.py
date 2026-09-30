"""LOT-26 semantic schema tests for CFA FRA cutover artifacts."""

from __future__ import annotations

import json

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    CutoverArtifactSchemaError,
    LEGACY_IDENTITIES_SCHEMA,
    REGULATORY_AUTHORITY_SCHEMA,
    LegacyIdentityMigrationArtifact,
    RegulatoryAuthorityCutoverArtifact,
    parse_cutover_artifact,
)


def _identity_payload() -> dict[str, object]:
    return {
        "schema": LEGACY_IDENTITIES_SCHEMA,
        "kind": "legacy_identity_migration",
        "consumer": "CFA FRA",
        "generated_at": "2026-09-30T12:30:00Z",
        "source_system": "CFA_FRA_LEGACY",
        "target_system": "PYACCOUNTINGKIT",
        "summary": {
            "total_legacy_records": 1,
            "mapped_records": 1,
            "unresolved_records": 0,
        },
        "mappings": [
            {
                "legacy_type": "JournalEntry",
                "legacy_id": "legacy-entry-1",
                "target_type": "JournalEntry",
                "target_id": "target-entry-1",
                "source": "CFA_FRA_LEGACY",
                "source_checksum": "sha256:" + ("a" * 64),
            }
        ],
    }


def _authority_payload() -> dict[str, object]:
    return {
        "schema": REGULATORY_AUTHORITY_SCHEMA,
        "kind": "regulatory_authority_cutover",
        "consumer": "CFA FRA",
        "observed_at": "2026-09-30T12:30:00Z",
        "provider": {
            "name": "PyAccountingKit",
            "version": "0.6.0b16",
        },
        "routing_profile": "target_only",
        "local_framework_account_authority": False,
        "local_seed_commands_authoritative": False,
        "effective_plan_delegated": True,
        "sample_resolutions": [
            {
                "standard_id": "SYSCOHADA",
                "edition": "2017",
                "reference_key": "101000",
                "target_reference_id": "reference-101000",
            }
        ],
    }


def test_identity_artifact_requires_complete_traceable_mapping() -> None:
    artifact = LegacyIdentityMigrationArtifact.from_mapping(_identity_payload())

    assert len(artifact.links) == 1
    assert artifact.links[0].legacy_id == "legacy-entry-1"
    assert artifact.links[0].target_id == "target-entry-1"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("unresolved_records", 1),
        ("mapped_records", 0),
        ("total_legacy_records", 2),
    ],
)
def test_identity_artifact_rejects_incomplete_summary(field: str, value: int) -> None:
    payload = _identity_payload()
    payload["summary"][field] = value

    with pytest.raises(CutoverArtifactSchemaError):
        LegacyIdentityMigrationArtifact.from_mapping(payload)


def test_identity_artifact_rejects_duplicate_legacy_identity() -> None:
    payload = _identity_payload()
    payload["summary"] = {
        "total_legacy_records": 2,
        "mapped_records": 2,
        "unresolved_records": 0,
    }
    payload["mappings"] = [payload["mappings"][0], dict(payload["mappings"][0])]

    with pytest.raises(CutoverArtifactSchemaError, match="duplicate legacy identity"):
        LegacyIdentityMigrationArtifact.from_mapping(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("local_framework_account_authority", True),
        ("local_seed_commands_authoritative", True),
        ("effective_plan_delegated", False),
        ("routing_profile", "legacy"),
    ],
)
def test_regulatory_artifact_rejects_non_cutover_state(field: str, value: object) -> None:
    payload = _authority_payload()
    payload[field] = value

    with pytest.raises(CutoverArtifactSchemaError):
        RegulatoryAuthorityCutoverArtifact.from_mapping(payload)


def test_regulatory_artifact_requires_provider_resolution_samples() -> None:
    payload = _authority_payload()
    payload["sample_resolutions"] = []

    with pytest.raises(CutoverArtifactSchemaError, match="sampled provider resolutions"):
        RegulatoryAuthorityCutoverArtifact.from_mapping(payload)


def test_parser_rejects_artifact_type_mismatch(tmp_path) -> None:
    artifact = tmp_path / "authority.json"
    artifact.write_text(json.dumps(_authority_payload()), encoding="utf-8")

    with pytest.raises(CutoverArtifactSchemaError, match="legacy identity artifact schema"):
        parse_cutover_artifact("legacy_identities", artifact)


def test_parser_accepts_matching_authority_artifact(tmp_path) -> None:
    artifact = tmp_path / "authority.json"
    artifact.write_text(json.dumps(_authority_payload()), encoding="utf-8")

    parsed = parse_cutover_artifact("regulatory_authority", artifact)

    assert isinstance(parsed, RegulatoryAuthorityCutoverArtifact)
    assert parsed.provider_name == "PyAccountingKit"
