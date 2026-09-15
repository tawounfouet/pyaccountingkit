"""Regulatory account bindings and mapping candidates (LOT-11).

A ``MappingCandidate`` is a suggested company-to-reference mapping that must be
explicitly promoted before it becomes an active ``RegulatoryAccountBinding``
(ADR COA-024).  A binding version trail keeps historical mappings explainable
(ADR COA-018, spec sections 61-67 of the chart architecture).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyaccountingkit.core.errors import AccountRuleError


class BindingStatus(StrEnum):
    """Lifecycle of a company-to-reference mapping."""

    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class BindingPurpose(StrEnum):
    """Why a company account is linked to a reference account."""

    PRIMARY_STATUTORY = "PRIMARY_STATUTORY"
    SECONDARY_REPORTING = "SECONDARY_REPORTING"
    MIGRATION = "MIGRATION"
    CONSOLIDATION = "CONSOLIDATION"
    ANALYTICAL = "ANALYTICAL"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class MappingCandidate:
    """A proposed mapping, explicitly separated from active bindings."""

    id: str
    company_account_code: str
    reference_node_id: str
    reference_standard_id: str
    reference_snapshot_id: str
    reason: str = ""

    def __post_init__(self) -> None:
        for field_name, value in (
            ("id", self.id),
            ("company_account_code", self.company_account_code),
            ("reference_node_id", self.reference_node_id),
            ("reference_standard_id", self.reference_standard_id),
            ("reference_snapshot_id", self.reference_snapshot_id),
        ):
            if not value:
                raise AccountRuleError(f"{field_name} must be non-empty")


@dataclass(frozen=True, slots=True)
class RegulatoryAccountBinding:
    """An active, purpose-typed link between a company account and a reference."""

    id: str
    company_account_code: str
    reference_node_id: str
    reference_standard_id: str
    reference_snapshot_id: str
    purpose: BindingPurpose = BindingPurpose.PRIMARY_STATUTORY
    status: BindingStatus = BindingStatus.ACTIVE
    effective_from: date | None = None
    effective_to: date | None = None
    provenance: str = "generation"

    def __post_init__(self) -> None:
        for field_name, value in (
            ("id", self.id),
            ("company_account_code", self.company_account_code),
            ("reference_node_id", self.reference_node_id),
        ):
            if not value:
                raise AccountRuleError(f"{field_name} must be non-empty")
        if self.status is BindingStatus.CANDIDATE:
            raise AccountRuleError("A binding is active or retired, never a candidate")
        if self.effective_to is not None and self.effective_from is not None:
            if self.effective_to < self.effective_from:
                raise AccountRuleError("effective_to precedes effective_from")


@dataclass(frozen=True, slots=True)
class RegulatoryAccountBindingVersion:
    """One historical version of a binding, kept for explicability."""

    binding_id: str
    company_account_code: str
    version: int
    reference_node_id: str
    purpose: BindingPurpose
    effective_from: date | None = None
    effective_to: date | None = None

    def __post_init__(self) -> None:
        if self.version <= 0:
            raise AccountRuleError("binding version must be positive")


class ChartBindingRegistry:
    """Immutable registry separating mapping candidates from active bindings."""

    def __init__(
        self,
        bindings: tuple[RegulatoryAccountBinding, ...] = (),
        candidates: tuple[MappingCandidate, ...] = (),
        versions: tuple[RegulatoryAccountBindingVersion, ...] = (),
    ) -> None:
        self._bindings = bindings
        self._candidates = candidates
        self._versions = versions
        self._validate()

    def _validate(self) -> None:
        binding_ids = [binding.id for binding in self._bindings]
        if len(binding_ids) != len(set(binding_ids)):
            raise AccountRuleError("duplicate binding ids")
        candidate_ids = [candidate.id for candidate in self._candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise AccountRuleError("duplicate candidate ids")
        primary_keys = {
            binding.company_account_code
            for binding in self._bindings
            if binding.purpose is BindingPurpose.PRIMARY_STATUTORY
        }
        if len(primary_keys) != sum(
            1 for binding in self._bindings if binding.purpose is BindingPurpose.PRIMARY_STATUTORY
        ):
            raise AccountRuleError("at most one active PRIMARY_STATUTORY binding per company code")

    def bindings(self) -> tuple[RegulatoryAccountBinding, ...]:
        return self._bindings

    def candidates(self) -> tuple[MappingCandidate, ...]:
        return self._candidates

    def versions(self) -> tuple[RegulatoryAccountBindingVersion, ...]:
        return self._versions

    def active_binding_for_company(
        self,
        company_code: str,
        purpose: BindingPurpose = BindingPurpose.PRIMARY_STATUTORY,
    ) -> RegulatoryAccountBinding | None:
        for binding in self._bindings:
            if binding.company_account_code == company_code and binding.purpose is purpose:
                return binding
        return None

    def bindings_for_reference(
        self, reference_node_id: str
    ) -> tuple[RegulatoryAccountBinding, ...]:
        return tuple(
            binding for binding in self._bindings if binding.reference_node_id == reference_node_id
        )

    def candidates_for_reference(self, reference_node_id: str) -> tuple[MappingCandidate, ...]:
        return tuple(
            candidate
            for candidate in self._candidates
            if candidate.reference_node_id == reference_node_id
        )

    def add_candidate(self, candidate: MappingCandidate) -> ChartBindingRegistry:
        for existing in self._candidates:
            if existing.company_account_code == candidate.company_account_code:
                raise AccountRuleError(
                    f"candidate already exists for {candidate.company_account_code!r}"
                )
        return ChartBindingRegistry(
            bindings=self._bindings,
            candidates=(*self._candidates, candidate),
            versions=self._versions,
        )

    def promote_candidate(
        self,
        candidate: MappingCandidate,
        *,
        purpose: BindingPurpose,
        effective_from: date | None = None,
        provenance: str = "registry",
    ) -> tuple[ChartBindingRegistry, RegulatoryAccountBinding]:
        """Promote a candidate into an active binding (ADR COA-024)."""
        if all(existing.id != candidate.id for existing in self._candidates):
            raise AccountRuleError(f"candidate {candidate.id!r} not found")
        binding = RegulatoryAccountBinding(
            id=candidate.id,
            company_account_code=candidate.company_account_code,
            reference_node_id=candidate.reference_node_id,
            reference_standard_id=candidate.reference_standard_id,
            reference_snapshot_id=candidate.reference_snapshot_id,
            purpose=purpose,
            effective_from=effective_from,
            provenance=provenance,
        )
        remaining = tuple(item for item in self._candidates if item.id != candidate.id)
        version = self._next_version_number(binding.company_account_code)
        registry = ChartBindingRegistry(
            bindings=(*self._bindings, binding),
            candidates=remaining,
            versions=self._versions
            + (
                RegulatoryAccountBindingVersion(
                    binding_id=binding.id,
                    company_account_code=binding.company_account_code,
                    version=version,
                    reference_node_id=binding.reference_node_id,
                    purpose=binding.purpose,
                    effective_from=binding.effective_from,
                ),
            ),
        )
        return registry, binding

    def retire(
        self,
        company_code: str,
        *,
        purpose: BindingPurpose = BindingPurpose.PRIMARY_STATUTORY,
        effective_to: date | None = None,
    ) -> ChartBindingRegistry:
        """Retire the active binding of a company code without deleting history."""
        binding = self.active_binding_for_company(company_code, purpose)
        if binding is None:
            raise AccountRuleError(f"no active {purpose.value} binding for {company_code!r}")
        updated = tuple(
            RegulatoryAccountBinding(
                id=item.id,
                company_account_code=item.company_account_code,
                reference_node_id=item.reference_node_id,
                reference_standard_id=item.reference_standard_id,
                reference_snapshot_id=item.reference_snapshot_id,
                purpose=item.purpose,
                status=BindingStatus.RETIRED,
                effective_from=item.effective_from,
                effective_to=effective_to or item.effective_to,
                provenance=item.provenance,
            )
            if item.company_account_code == company_code and item is binding
            else item
            for item in self._bindings
        )
        return ChartBindingRegistry(
            bindings=updated,
            candidates=self._candidates,
            versions=self._versions,
        )

    def _next_version_number(self, company_code: str) -> int:
        return sum(1 for v in self._versions if v.company_account_code == company_code) + 1


__all__ = [
    "BindingPurpose",
    "BindingStatus",
    "ChartBindingRegistry",
    "MappingCandidate",
    "RegulatoryAccountBinding",
    "RegulatoryAccountBindingVersion",
]
