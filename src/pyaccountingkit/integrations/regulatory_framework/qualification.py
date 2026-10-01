"""Capability-scoped regulatory production qualification contracts (LOT-27)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RegulatoryCapabilityCode(StrEnum):
    """Independent regulatory integration capabilities."""

    STRUCTURE = "STRUCTURE"
    EFFECTIVE_PLAN = "EFFECTIVE_PLAN"
    OVERLAYS = "OVERLAYS"
    RELATIONS = "RELATIONS"
    CROSSWALKS = "CROSSWALKS"
    NEGATIVE_CONSTRAINTS = "NEGATIVE_CONSTRAINTS"
    CONCEPTS = "CONCEPTS"
    CONCEPT_BINDINGS = "CONCEPT_BINDINGS"
    REPORTING_STRUCTURE = "REPORTING_STRUCTURE"
    REPORTING_ACCOUNT_MAPPINGS = "REPORTING_ACCOUNT_MAPPINGS"
    POLICIES = "POLICIES"
    EXPORTS = "EXPORTS"
    SNAPSHOTS = "SNAPSHOTS"


class RegulatoryCapabilityStatus(StrEnum):
    """Authority level attached to one capability, never to a whole standard."""

    NOT_ASSERTED = "NOT_ASSERTED"
    DISCOVERED = "DISCOVERED"
    INGESTIBLE = "INGESTIBLE"
    VALIDATED = "VALIDATED"
    CANDIDATE = "CANDIDATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    EXECUTABLE = "EXECUTABLE"
    PRODUCTION_QUALIFIED = "PRODUCTION_QUALIFIED"
    FORBIDDEN_INFERENCE = "FORBIDDEN_INFERENCE"


class RegulatorySupportLevel(StrEnum):
    """Derived support level for one capability."""

    NOT_ASSERTED = "NOT_ASSERTED"
    DISCOVERED = "DISCOVERED"
    REFERENCE_VALIDATED = "REFERENCE_VALIDATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    EXECUTABLE = "EXECUTABLE"
    PRODUCTION_QUALIFIED = "PRODUCTION_QUALIFIED"
    FORBIDDEN_INFERENCE = "FORBIDDEN_INFERENCE"


_STATUS_LEVEL: dict[RegulatoryCapabilityStatus, RegulatorySupportLevel] = {
    RegulatoryCapabilityStatus.NOT_ASSERTED: RegulatorySupportLevel.NOT_ASSERTED,
    RegulatoryCapabilityStatus.DISCOVERED: RegulatorySupportLevel.DISCOVERED,
    RegulatoryCapabilityStatus.INGESTIBLE: RegulatorySupportLevel.DISCOVERED,
    RegulatoryCapabilityStatus.VALIDATED: RegulatorySupportLevel.REFERENCE_VALIDATED,
    RegulatoryCapabilityStatus.CANDIDATE: RegulatorySupportLevel.REVIEW_REQUIRED,
    RegulatoryCapabilityStatus.REVIEW_REQUIRED: RegulatorySupportLevel.REVIEW_REQUIRED,
    RegulatoryCapabilityStatus.EXECUTABLE: RegulatorySupportLevel.EXECUTABLE,
    RegulatoryCapabilityStatus.PRODUCTION_QUALIFIED: RegulatorySupportLevel.PRODUCTION_QUALIFIED,
    RegulatoryCapabilityStatus.FORBIDDEN_INFERENCE: RegulatorySupportLevel.FORBIDDEN_INFERENCE,
}


@dataclass(frozen=True, slots=True)
class RegulatoryCapabilityQualification:
    """Auditable qualification record for exactly one regulatory capability."""

    standard_ref: str
    capability_code: RegulatoryCapabilityCode
    provider_version: str
    dataset_release: str
    framework_version: str
    status: RegulatoryCapabilityStatus
    evidence_refs: tuple[str, ...] = ()
    executable: bool = False
    human_review_required: bool = False
    auto_inference_allowed: bool = False
    test_suite: str | None = None
    golden_refs: tuple[str, ...] = ()
    reviewer: str | None = None
    qualified_at: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "standard_ref",
            "provider_version",
            "dataset_release",
            "framework_version",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be non-empty")

        if self.executable and self.status not in {
            RegulatoryCapabilityStatus.EXECUTABLE,
            RegulatoryCapabilityStatus.PRODUCTION_QUALIFIED,
        }:
            raise ValueError("only EXECUTABLE/PRODUCTION_QUALIFIED capability may execute")

        if self.status in {
            RegulatoryCapabilityStatus.NOT_ASSERTED,
            RegulatoryCapabilityStatus.CANDIDATE,
            RegulatoryCapabilityStatus.REVIEW_REQUIRED,
            RegulatoryCapabilityStatus.FORBIDDEN_INFERENCE,
        } and self.executable:
            raise ValueError(f"{self.status.value} capability must be non-executable")

        if (
            self.status is RegulatoryCapabilityStatus.REVIEW_REQUIRED
            and not self.human_review_required
        ):
            raise ValueError("REVIEW_REQUIRED capability must require human review")

        if (
            self.status is RegulatoryCapabilityStatus.FORBIDDEN_INFERENCE
            and self.auto_inference_allowed
        ):
            raise ValueError("FORBIDDEN_INFERENCE cannot allow automatic inference")

        if self.status is RegulatoryCapabilityStatus.PRODUCTION_QUALIFIED:
            if not self.executable:
                raise ValueError("PRODUCTION_QUALIFIED capability must be executable")
            if not self.evidence_refs or not self.golden_refs or not self.test_suite:
                raise ValueError(
                    "PRODUCTION_QUALIFIED capability requires evidence, golden refs and test suite"
                )
            if not self.reviewer or not self.qualified_at:
                raise ValueError(
                    "PRODUCTION_QUALIFIED capability requires reviewer and qualification time"
                )

        if self.qualified_at is not None:
            if not self.qualified_at.endswith("Z"):
                raise ValueError("qualified_at must use UTC Z suffix")
            datetime.fromisoformat(self.qualified_at[:-1] + "+00:00")

    @property
    def support_level(self) -> RegulatorySupportLevel:
        return _STATUS_LEVEL[self.status]

    def to_payload(self) -> dict[str, object]:
        return {
            "capability": self.capability_code.value,
            "status": self.status.value,
            "support_level": self.support_level.value,
            "provider_version": self.provider_version,
            "dataset_release": self.dataset_release,
            "framework_version": self.framework_version,
            "evidence_refs": list(self.evidence_refs),
            "executable": self.executable,
            "human_review_required": self.human_review_required,
            "auto_inference_allowed": self.auto_inference_allowed,
            "test_suite": self.test_suite,
            "golden_refs": list(self.golden_refs),
            "reviewer": self.reviewer,
            "qualified_at": self.qualified_at,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class RegulatoryFrameworkIntegrationProfile:
    """Capability-scoped qualification profile for one canonical standard reference."""

    profile_id: str
    standard_ref: str
    provider_id: str
    dataset_release: str
    tested_framework_version: str
    capabilities: tuple[RegulatoryCapabilityQualification, ...]

    def __post_init__(self) -> None:
        if not self.profile_id.strip() or not self.standard_ref.strip() or not self.provider_id.strip():
            raise ValueError("profile identity fields must be non-empty")
        if not self.dataset_release.strip() or not self.tested_framework_version.strip():
            raise ValueError("profile version fields must be non-empty")

        codes: set[RegulatoryCapabilityCode] = set()
        for qualification in self.capabilities:
            if qualification.standard_ref != self.standard_ref:
                raise ValueError("capability standard_ref must match profile standard_ref")
            if qualification.capability_code in codes:
                raise ValueError(
                    f"duplicate capability {qualification.capability_code.value} in profile"
                )
            codes.add(qualification.capability_code)

    def qualification_for(
        self,
        capability: RegulatoryCapabilityCode,
    ) -> RegulatoryCapabilityQualification | None:
        for qualification in self.capabilities:
            if qualification.capability_code is capability:
                return qualification
        return None

    @property
    def production_qualified_capabilities(self) -> tuple[RegulatoryCapabilityCode, ...]:
        return tuple(
            qualification.capability_code
            for qualification in self.capabilities
            if qualification.status is RegulatoryCapabilityStatus.PRODUCTION_QUALIFIED
        )

    def to_payload(self) -> dict[str, object]:
        ordered = sorted(self.capabilities, key=lambda item: item.capability_code.value)
        return {
            "profile_id": self.profile_id,
            "standard_ref": self.standard_ref,
            "provider_id": self.provider_id,
            "dataset_release": self.dataset_release,
            "tested_framework_version": self.tested_framework_version,
            "qualification_scope": "CAPABILITY_SCOPED",
            "production_qualified_capabilities": [
                code.value for code in self.production_qualified_capabilities
            ],
            "capabilities": {
                qualification.capability_code.value: qualification.to_payload()
                for qualification in ordered
            },
        }


__all__ = [
    "RegulatoryCapabilityCode",
    "RegulatoryCapabilityQualification",
    "RegulatoryCapabilityStatus",
    "RegulatoryFrameworkIntegrationProfile",
    "RegulatorySupportLevel",
]
