"""Deterministic generation of CFA FRA cutover evidence artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pyaccountingkit.integrations.cfa_fra.compatibility import (
    LegacyIdentityLink,
    LegacyIdentityStoreProtocol,
    MigrationRouting,
)
from pyaccountingkit.integrations.cfa_fra.cutover_artifact_schema import (
    LEGACY_IDENTITIES_SCHEMA,
    REGULATORY_AUTHORITY_SCHEMA,
    CutoverArtifactKey,
    LegacyIdentityMigrationArtifact,
    RegulatoryAuthorityCutoverArtifact,
    RegulatoryAuthorityResolution,
)


class CutoverArtifactGenerationError(ValueError):
    """Raised when source observations cannot support a qualified artifact."""


@dataclass(frozen=True, slots=True)
class RegulatoryAuthorityObservation:
    """Observed consumer state required to generate authority-cutover evidence."""

    provider_name: str
    provider_version: str
    routing: MigrationRouting
    local_framework_account_authority: bool
    local_seed_commands_authoritative: bool
    effective_plan_delegated: bool
    resolutions: tuple[RegulatoryAuthorityResolution, ...]

    def __post_init__(self) -> None:
        if not self.provider_name.strip():
            raise CutoverArtifactGenerationError("provider_name must not be empty")
        if not self.provider_version.strip():
            raise CutoverArtifactGenerationError("provider_version must not be empty")


@dataclass(frozen=True, slots=True)
class GeneratedCutoverArtifact:
    """One generated artifact after semantic self-validation."""

    key: CutoverArtifactKey
    payload: Mapping[str, object]


def _identity_record(link: LegacyIdentityLink) -> dict[str, object]:
    record: dict[str, object] = {
        "legacy_type": link.legacy_type,
        "legacy_id": link.legacy_id,
        "target_type": link.target_type,
        "target_id": link.target_id,
        "source": link.source,
    }
    if link.source_checksum is not None:
        record["source_checksum"] = link.source_checksum
    return record


def generate_legacy_identity_artifact(
    *,
    consumer: str,
    generated_at: str,
    identities: LegacyIdentityStoreProtocol,
    expected_legacy_records: int,
) -> GeneratedCutoverArtifact:
    """Generate complete identity evidence from a migrated identity-store snapshot."""
    if expected_legacy_records <= 0:
        raise CutoverArtifactGenerationError("expected_legacy_records must be greater than zero")

    links = tuple(
        sorted(
            identities.snapshot(),
            key=lambda item: (item.legacy_type, item.legacy_id),
        )
    )
    if len(links) != expected_legacy_records:
        raise CutoverArtifactGenerationError(
            "identity snapshot is incomplete: "
            f"expected {expected_legacy_records}, found {len(links)}"
        )

    payload: dict[str, object] = {
        "schema": LEGACY_IDENTITIES_SCHEMA,
        "kind": "legacy_identity_migration",
        "consumer": consumer,
        "generated_at": generated_at,
        "source_system": "CFA_FRA_LEGACY",
        "target_system": "PYACCOUNTINGKIT",
        "summary": {
            "total_legacy_records": expected_legacy_records,
            "mapped_records": len(links),
            "unresolved_records": expected_legacy_records - len(links),
        },
        "mappings": [_identity_record(link) for link in links],
    }

    try:
        LegacyIdentityMigrationArtifact.from_mapping(payload)
    except ValueError as exc:
        raise CutoverArtifactGenerationError(str(exc)) from exc

    return GeneratedCutoverArtifact(key="legacy_identities", payload=payload)


def generate_regulatory_authority_artifact(
    *,
    consumer: str,
    observed_at: str,
    observation: RegulatoryAuthorityObservation,
) -> GeneratedCutoverArtifact:
    """Generate provider-cutover evidence from an observed consumer state."""
    if not observation.routing.is_target_only():
        raise CutoverArtifactGenerationError(
            "regulatory authority evidence requires target-only routing"
        )
    if observation.provider_name != "PyAccountingKit":
        raise CutoverArtifactGenerationError(
            "regulatory authority evidence requires PyAccountingKit provider"
        )
    if observation.local_framework_account_authority:
        raise CutoverArtifactGenerationError(
            "local FrameworkAccount authority must be disabled before evidence generation"
        )
    if observation.local_seed_commands_authoritative:
        raise CutoverArtifactGenerationError(
            "local regulatory seed commands must be non-authoritative before evidence generation"
        )
    if not observation.effective_plan_delegated:
        raise CutoverArtifactGenerationError(
            "effective_plan must delegate to PyAccountingKit before evidence generation"
        )
    if not observation.resolutions:
        raise CutoverArtifactGenerationError(
            "at least one provider-backed reference resolution is required"
        )

    resolutions = tuple(
        sorted(
            observation.resolutions,
            key=lambda item: (item.standard_id, item.edition, item.reference_key),
        )
    )
    payload: dict[str, object] = {
        "schema": REGULATORY_AUTHORITY_SCHEMA,
        "kind": "regulatory_authority_cutover",
        "consumer": consumer,
        "observed_at": observed_at,
        "provider": {
            "name": observation.provider_name,
            "version": observation.provider_version,
        },
        "routing_profile": "target_only",
        "local_framework_account_authority": False,
        "local_seed_commands_authoritative": False,
        "effective_plan_delegated": True,
        "sample_resolutions": [
            {
                "standard_id": resolution.standard_id,
                "edition": resolution.edition,
                "reference_key": resolution.reference_key,
                "target_reference_id": resolution.target_reference_id,
            }
            for resolution in resolutions
        ],
    }

    try:
        RegulatoryAuthorityCutoverArtifact.from_mapping(payload)
    except ValueError as exc:
        raise CutoverArtifactGenerationError(str(exc)) from exc

    return GeneratedCutoverArtifact(key="regulatory_authority", payload=payload)


def generation_payload(
    artifact: GeneratedCutoverArtifact,
) -> dict[str, object]:
    """Return a mutable deterministic JSON-ready copy of generated evidence."""
    return dict(artifact.payload)


__all__ = [
    "CutoverArtifactGenerationError",
    "GeneratedCutoverArtifact",
    "RegulatoryAuthorityObservation",
    "generate_legacy_identity_artifact",
    "generate_regulatory_authority_artifact",
    "generation_payload",
]
