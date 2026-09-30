"""Deterministic generation of CFA FRA cutover evidence artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pyaccountingkit.integrations.cfa_fra.compatibility import (
    LegacyIdentityLink,
    LegacyIdentityMap,
    LegacyIdentityStoreProtocol,
    MigrationRouting,
)
from pyaccountingkit.integrations.cfa_fra.cutover_artifact_schema import (
    CONSUMER_E2E_SCHEMA,
    LEGACY_IDENTITIES_SCHEMA,
    REGULATORY_AUTHORITY_SCHEMA,
    ConsumerE2ECutoverArtifact,
    CutoverArtifactKey,
    LegacyIdentityMigrationArtifact,
    RegulatoryAuthorityCutoverArtifact,
    RegulatoryAuthorityResolution,
)


class CutoverArtifactGenerationError(ValueError):
    """Raised when source observations cannot support a qualified artifact."""


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise CutoverArtifactGenerationError(f"{field} must be a JSON object")
    return value


def _string(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CutoverArtifactGenerationError(f"{field} must be a non-empty string")
    return value


def _integer(payload: Mapping[str, object], field: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CutoverArtifactGenerationError(f"{field} must be an integer")
    return value


def _boolean(payload: Mapping[str, object], field: str) -> bool:
    value = payload.get(field)
    if not isinstance(value, bool):
        raise CutoverArtifactGenerationError(f"{field} must be boolean")
    return value


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


def generate_consumer_e2e_artifact(
    *,
    consumer: str,
    observed_at: str,
    environment: str,
    producer: str,
    scenarios: list[Mapping[str, object]],
) -> GeneratedCutoverArtifact:
    """Generate live consumer E2E evidence from structured scenario observations."""
    payload: dict[str, object] = {
        "schema": CONSUMER_E2E_SCHEMA,
        "kind": "consumer_e2e_cutover",
        "consumer": consumer,
        "observed_at": observed_at,
        "environment": environment,
        "producer": producer,
        "routing_profile": "target_only",
        "scenarios": [dict(item) for item in scenarios],
    }

    try:
        ConsumerE2ECutoverArtifact.from_mapping(payload)
    except ValueError as exc:
        raise CutoverArtifactGenerationError(str(exc)) from exc

    return GeneratedCutoverArtifact(key="consumer_e2e", payload=payload)


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


def generate_cutover_artifact_from_mapping(
    key: CutoverArtifactKey,
    payload: Mapping[str, object],
) -> GeneratedCutoverArtifact:
    """Generate one cutover artifact from a structured observation snapshot."""
    if key == "consumer_e2e":
        raw_scenarios = payload.get("scenarios")
        if not isinstance(raw_scenarios, list):
            raise CutoverArtifactGenerationError("scenarios must be a JSON array")
        scenarios = [
            dict(_mapping(raw, f"scenarios[{index}]"))
            for index, raw in enumerate(raw_scenarios)
        ]
        return generate_consumer_e2e_artifact(
            consumer=_string(payload, "consumer"),
            observed_at=_string(payload, "observed_at"),
            environment=_string(payload, "environment"),
            producer=_string(payload, "producer"),
            scenarios=scenarios,
        )

    if key == "legacy_identities":
        raw_links = payload.get("links")
        if not isinstance(raw_links, list):
            raise CutoverArtifactGenerationError("links must be a JSON array")

        links: list[LegacyIdentityLink] = []
        for index, raw in enumerate(raw_links):
            item = _mapping(raw, f"links[{index}]")
            checksum = item.get("source_checksum")
            if checksum is not None and not isinstance(checksum, str):
                raise CutoverArtifactGenerationError(
                    f"links[{index}].source_checksum must be a string"
                )
            links.append(
                LegacyIdentityLink(
                    legacy_type=_string(item, "legacy_type"),
                    legacy_id=_string(item, "legacy_id"),
                    target_type=_string(item, "target_type"),
                    target_id=_string(item, "target_id"),
                    source=_string(item, "source"),
                    source_checksum=checksum,
                )
            )

        return generate_legacy_identity_artifact(
            consumer=_string(payload, "consumer"),
            generated_at=_string(payload, "generated_at"),
            identities=LegacyIdentityMap(tuple(links)),
            expected_legacy_records=_integer(payload, "expected_legacy_records"),
        )

    provider = _mapping(payload.get("provider"), "provider")
    raw_resolutions = payload.get("sample_resolutions")
    if not isinstance(raw_resolutions, list):
        raise CutoverArtifactGenerationError("sample_resolutions must be a JSON array")

    resolutions = tuple(
        RegulatoryAuthorityResolution(
            standard_id=_string(_mapping(raw, f"sample_resolutions[{index}]"), "standard_id"),
            edition=_string(_mapping(raw, f"sample_resolutions[{index}]"), "edition"),
            reference_key=_string(
                _mapping(raw, f"sample_resolutions[{index}]"),
                "reference_key",
            ),
            target_reference_id=_string(
                _mapping(raw, f"sample_resolutions[{index}]"),
                "target_reference_id",
            ),
        )
        for index, raw in enumerate(raw_resolutions)
    )
    routing_profile = _string(payload, "routing_profile")
    routing = (
        MigrationRouting.target_only() if routing_profile == "target_only" else MigrationRouting()
    )

    return generate_regulatory_authority_artifact(
        consumer=_string(payload, "consumer"),
        observed_at=_string(payload, "observed_at"),
        observation=RegulatoryAuthorityObservation(
            provider_name=_string(provider, "name"),
            provider_version=_string(provider, "version"),
            routing=routing,
            local_framework_account_authority=_boolean(
                payload,
                "local_framework_account_authority",
            ),
            local_seed_commands_authoritative=_boolean(
                payload,
                "local_seed_commands_authoritative",
            ),
            effective_plan_delegated=_boolean(payload, "effective_plan_delegated"),
            resolutions=resolutions,
        ),
    )


def generation_payload(
    artifact: GeneratedCutoverArtifact,
) -> dict[str, object]:
    """Return a mutable deterministic JSON-ready copy of generated evidence."""
    return dict(artifact.payload)


__all__ = [
    "CutoverArtifactGenerationError",
    "GeneratedCutoverArtifact",
    "RegulatoryAuthorityObservation",
    "generate_consumer_e2e_artifact",
    "generate_cutover_artifact_from_mapping",
    "generate_legacy_identity_artifact",
    "generate_regulatory_authority_artifact",
    "generation_payload",
]
