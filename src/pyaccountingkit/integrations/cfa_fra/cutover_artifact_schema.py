"""Semantic schemas for CFA FRA live cutover evidence artifacts."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from pyaccountingkit.integrations.cfa_fra.compatibility import LegacyIdentityLink
from pyaccountingkit.integrations.cfa_fra.consumer_qualification import (
    CFAFRAConsumerQualificationError,
    ConsumerQualification,
    ConsumerScenario,
    ConsumerScenarioEvidence,
    ConsumerScenarioStatus,
)

CutoverArtifactKey = Literal[
    "consumer_e2e",
    "legacy_identities",
    "regulatory_authority",
]

CONSUMER_E2E_SCHEMA = "cfa_fra_consumer_e2e_cutover/v1"
LEGACY_IDENTITIES_SCHEMA = "cfa_fra_legacy_identity_migration/v1"
REGULATORY_AUTHORITY_SCHEMA = "cfa_fra_regulatory_authority_cutover/v1"

_SHA256_PREFIXED = re.compile(r"^sha256:[0-9a-f]{64}$")


class CutoverArtifactSchemaError(ValueError):
    """Raised when a live cutover artifact is semantically invalid."""


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise CutoverArtifactSchemaError(f"{field} must be a JSON object")
    return cast(Mapping[str, object], value)


def _string(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CutoverArtifactSchemaError(f"{field} must be a non-empty string")
    return value


def _integer(payload: Mapping[str, object], field: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CutoverArtifactSchemaError(f"{field} must be a non-negative integer")
    return value


def _boolean(payload: Mapping[str, object], field: str) -> bool:
    value = payload.get(field)
    if not isinstance(value, bool):
        raise CutoverArtifactSchemaError(f"{field} must be boolean")
    return value


def _utc_timestamp(payload: Mapping[str, object], field: str) -> str:
    value = _string(payload, field)
    if not value.endswith("Z"):
        raise CutoverArtifactSchemaError(f"{field} must use an explicit UTC Z suffix")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CutoverArtifactSchemaError(f"{field} must be ISO-8601") from exc
    offset = parsed.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise CutoverArtifactSchemaError(f"{field} must be UTC")
    return value


@dataclass(frozen=True, slots=True)
class ConsumerE2ECutoverArtifact:
    """Evidence that every mandatory CFA FRA consumer scenario passes live."""

    consumer: str
    observed_at: str
    environment: str
    producer: str
    evidence: tuple[ConsumerScenarioEvidence, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> ConsumerE2ECutoverArtifact:
        if payload.get("schema") != CONSUMER_E2E_SCHEMA:
            raise CutoverArtifactSchemaError(
                f"consumer E2E artifact schema must be {CONSUMER_E2E_SCHEMA!r}"
            )
        if payload.get("kind") != "consumer_e2e_cutover":
            raise CutoverArtifactSchemaError(
                "consumer E2E artifact kind must be 'consumer_e2e_cutover'"
            )
        if payload.get("routing_profile") != "target_only":
            raise CutoverArtifactSchemaError(
                "consumer E2E PASS evidence requires target_only routing"
            )

        raw_scenarios = payload.get("scenarios")
        if not isinstance(raw_scenarios, list) or not raw_scenarios:
            raise CutoverArtifactSchemaError("consumer E2E artifact must contain scenario evidence")

        evidence: list[ConsumerScenarioEvidence] = []
        for index, raw in enumerate(raw_scenarios):
            item = _mapping(raw, f"scenarios[{index}]")
            raw_scenario = _string(item, "scenario")
            raw_status = _string(item, "status")
            source = _string(item, "source")
            checksum = _string(item, "evidence_checksum")
            if _SHA256_PREFIXED.fullmatch(checksum) is None:
                raise CutoverArtifactSchemaError(
                    f"scenarios[{index}].evidence_checksum must be sha256:<64 lowercase hex>"
                )
            try:
                scenario = ConsumerScenario(raw_scenario)
                status = ConsumerScenarioStatus(raw_status)
            except ValueError as exc:
                raise CutoverArtifactSchemaError(
                    f"scenarios[{index}] contains an invalid scenario or status"
                ) from exc
            if status is not ConsumerScenarioStatus.PASS:
                raise CutoverArtifactSchemaError(
                    f"scenarios[{index}] must be PASS for retirement evidence"
                )
            evidence.append(
                ConsumerScenarioEvidence(
                    scenario=scenario,
                    status=status,
                    source=source,
                    evidence_checksum=checksum,
                )
            )

        try:
            qualification = ConsumerQualification(tuple(evidence))
        except CFAFRAConsumerQualificationError as exc:
            raise CutoverArtifactSchemaError(str(exc)) from exc
        decision = qualification.evaluate()
        if not decision.green:
            raise CutoverArtifactSchemaError(
                "consumer E2E artifact must contain exactly one PASS for every mandatory scenario"
            )

        return cls(
            consumer=_string(payload, "consumer"),
            observed_at=_utc_timestamp(payload, "observed_at"),
            environment=_string(payload, "environment"),
            producer=_string(payload, "producer"),
            evidence=qualification.evidence(),
        )


@dataclass(frozen=True, slots=True)
class LegacyIdentityMigrationArtifact:
    """Complete legacy-to-target identity mapping evidence."""

    consumer: str
    generated_at: str
    source_system: str
    target_system: str
    links: tuple[LegacyIdentityLink, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> LegacyIdentityMigrationArtifact:
        if payload.get("schema") != LEGACY_IDENTITIES_SCHEMA:
            raise CutoverArtifactSchemaError(
                f"legacy identity artifact schema must be {LEGACY_IDENTITIES_SCHEMA!r}"
            )
        if payload.get("kind") != "legacy_identity_migration":
            raise CutoverArtifactSchemaError(
                "legacy identity artifact kind must be 'legacy_identity_migration'"
            )

        source_system = _string(payload, "source_system")
        target_system = _string(payload, "target_system")
        if source_system != "CFA_FRA_LEGACY":
            raise CutoverArtifactSchemaError(
                "legacy identity artifact source_system must be 'CFA_FRA_LEGACY'"
            )
        if target_system != "PYACCOUNTINGKIT":
            raise CutoverArtifactSchemaError(
                "legacy identity artifact target_system must be 'PYACCOUNTINGKIT'"
            )

        raw_summary = _mapping(payload.get("summary"), "summary")
        total = _integer(raw_summary, "total_legacy_records")
        mapped = _integer(raw_summary, "mapped_records")
        unresolved = _integer(raw_summary, "unresolved_records")
        if unresolved != 0:
            raise CutoverArtifactSchemaError(
                "legacy identity PASS evidence cannot contain unresolved records"
            )

        raw_mappings = payload.get("mappings")
        if not isinstance(raw_mappings, list) or not raw_mappings:
            raise CutoverArtifactSchemaError(
                "legacy identity artifact must contain at least one mapping"
            )

        links: list[LegacyIdentityLink] = []
        seen: set[tuple[str, str]] = set()
        for index, raw in enumerate(raw_mappings):
            item = _mapping(raw, f"mappings[{index}]")
            key = (_string(item, "legacy_type"), _string(item, "legacy_id"))
            if key in seen:
                raise CutoverArtifactSchemaError(
                    f"duplicate legacy identity mapping: {key[0]}:{key[1]}"
                )
            seen.add(key)

            checksum = item.get("source_checksum")
            if checksum is not None and (
                not isinstance(checksum, str) or _SHA256_PREFIXED.fullmatch(checksum) is None
            ):
                raise CutoverArtifactSchemaError(
                    f"mappings[{index}].source_checksum must be sha256:<64 lowercase hex>"
                )

            source = _string(item, "source")
            if source != source_system:
                raise CutoverArtifactSchemaError(
                    f"mappings[{index}].source must equal artifact source_system"
                )

            links.append(
                LegacyIdentityLink(
                    legacy_type=key[0],
                    legacy_id=key[1],
                    target_type=_string(item, "target_type"),
                    target_id=_string(item, "target_id"),
                    source=source,
                    source_checksum=checksum,
                )
            )

        if total != mapped or mapped != len(links):
            raise CutoverArtifactSchemaError(
                "identity summary must be complete and equal the mapping count"
            )

        return cls(
            consumer=_string(payload, "consumer"),
            generated_at=_utc_timestamp(payload, "generated_at"),
            source_system=source_system,
            target_system=target_system,
            links=tuple(links),
        )


@dataclass(frozen=True, slots=True)
class RegulatoryAuthorityResolution:
    """One sampled reference resolved through the target provider."""

    standard_id: str
    edition: str
    reference_key: str
    target_reference_id: str


@dataclass(frozen=True, slots=True)
class RegulatoryAuthorityCutoverArtifact:
    """Evidence that local CFA FRA reference authority has been replaced."""

    consumer: str
    observed_at: str
    provider_name: str
    provider_version: str
    resolutions: tuple[RegulatoryAuthorityResolution, ...]

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, object],
    ) -> RegulatoryAuthorityCutoverArtifact:
        if payload.get("schema") != REGULATORY_AUTHORITY_SCHEMA:
            raise CutoverArtifactSchemaError(
                f"regulatory authority artifact schema must be {REGULATORY_AUTHORITY_SCHEMA!r}"
            )
        if payload.get("kind") != "regulatory_authority_cutover":
            raise CutoverArtifactSchemaError(
                "regulatory authority artifact kind must be 'regulatory_authority_cutover'"
            )
        if payload.get("routing_profile") != "target_only":
            raise CutoverArtifactSchemaError(
                "regulatory authority PASS evidence requires target_only routing"
            )
        if _boolean(payload, "local_framework_account_authority") is not False:
            raise CutoverArtifactSchemaError("local FrameworkAccount authority must be disabled")
        if _boolean(payload, "local_seed_commands_authoritative") is not False:
            raise CutoverArtifactSchemaError(
                "local regulatory seed commands must not remain authoritative"
            )
        if _boolean(payload, "effective_plan_delegated") is not True:
            raise CutoverArtifactSchemaError("effective_plan must be delegated to PyAccountingKit")

        provider = _mapping(payload.get("provider"), "provider")
        raw_resolutions = payload.get("sample_resolutions")
        if not isinstance(raw_resolutions, list) or not raw_resolutions:
            raise CutoverArtifactSchemaError(
                "regulatory authority evidence requires sampled provider resolutions"
            )

        resolutions: list[RegulatoryAuthorityResolution] = []
        seen: set[tuple[str, str, str]] = set()
        for index, raw in enumerate(raw_resolutions):
            item = _mapping(raw, f"sample_resolutions[{index}]")
            key = (
                _string(item, "standard_id"),
                _string(item, "edition"),
                _string(item, "reference_key"),
            )
            if key in seen:
                raise CutoverArtifactSchemaError("duplicate regulatory authority sample resolution")
            seen.add(key)
            resolutions.append(
                RegulatoryAuthorityResolution(
                    standard_id=key[0],
                    edition=key[1],
                    reference_key=key[2],
                    target_reference_id=_string(item, "target_reference_id"),
                )
            )

        provider_name = _string(provider, "name")
        if provider_name != "PyAccountingKit":
            raise CutoverArtifactSchemaError(
                "regulatory authority provider.name must be 'PyAccountingKit'"
            )

        return cls(
            consumer=_string(payload, "consumer"),
            observed_at=_utc_timestamp(payload, "observed_at"),
            provider_name=provider_name,
            provider_version=_string(provider, "version"),
            resolutions=tuple(resolutions),
        )


CutoverArtifact = (
    ConsumerE2ECutoverArtifact
    | LegacyIdentityMigrationArtifact
    | RegulatoryAuthorityCutoverArtifact
)


def parse_cutover_artifact(
    key: CutoverArtifactKey,
    path: Path,
) -> CutoverArtifact:
    """Parse and semantically validate one materialized cutover artifact."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CutoverArtifactSchemaError(
            f"cutover artifact must be readable UTF-8 JSON: {path.name}"
        ) from exc

    payload = _mapping(raw, "artifact")
    if key == "consumer_e2e":
        return ConsumerE2ECutoverArtifact.from_mapping(payload)
    if key == "legacy_identities":
        return LegacyIdentityMigrationArtifact.from_mapping(payload)
    return RegulatoryAuthorityCutoverArtifact.from_mapping(payload)


__all__ = [
    "CutoverArtifact",
    "CutoverArtifactKey",
    "CutoverArtifactSchemaError",
    "CONSUMER_E2E_SCHEMA",
    "ConsumerE2ECutoverArtifact",
    "LEGACY_IDENTITIES_SCHEMA",
    "LegacyIdentityMigrationArtifact",
    "REGULATORY_AUTHORITY_SCHEMA",
    "RegulatoryAuthorityCutoverArtifact",
    "RegulatoryAuthorityResolution",
    "parse_cutover_artifact",
]
