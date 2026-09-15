"""Accounting policy set aggregate (LOT-12).

``AccountingPolicySet`` is the versioned aggregate root of the policies
bounded context (ADR-POL-001).  A set carries ``PolicyBinding`` entries that
pin a policy type, id and version with an applicability (ADR-POL-010/016).
Reference-data identity is pinned as a snapshot reference and never treated as
policy itself (ADR-POL-002/013, INV-POLSET-004).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any

from pyaccountingkit.core.errors import PolicyError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.policies.applicability import PolicyApplicability


class PolicyType(StrEnum):
    """Families of accounting policies (spec section 13)."""

    RECOGNITION = "RECOGNITION"
    MEASUREMENT = "MEASUREMENT"
    DEPRECIATION = "DEPRECIATION"
    IMPAIRMENT = "IMPAIRMENT"
    INVENTORY_VALUATION = "INVENTORY_VALUATION"
    ACCRUAL = "ACCRUAL"
    DEFERRAL = "DEFERRAL"
    PROVISION_RECOGNITION = "PROVISION_RECOGNITION"
    PROVISION_MEASUREMENT = "PROVISION_MEASUREMENT"
    ROUNDING = "ROUNDING"
    ENTRY_NUMBERING = "ENTRY_NUMBERING"
    REVERSAL_DATE = "REVERSAL_DATE"
    CLOSING = "CLOSING"
    OPENING_BALANCE = "OPENING_BALANCE"


class PolicySetStatus(StrEnum):
    """Lifecycle of an accounting policy set (spec section 10)."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class PolicyBinding:
    """A pinned reference to a concrete policy version for a given purpose."""

    policy_type: PolicyType
    policy_id: str
    policy_version: str
    applicability: PolicyApplicability = field(default_factory=PolicyApplicability)
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise PolicyError("policy_id must be non-empty")
        if not self.policy_version:
            raise PolicyError("policy_version must be non-empty")


@dataclass(frozen=True, slots=True)
class PolicySetReference:
    """Pinned reference-data identity of a policy set (INV-POLSET-004)."""

    standard_id: str
    edition: str
    dataset_version: str
    reference_snapshot_id: str

    def __post_init__(self) -> None:
        for name, value in (
            ("standard_id", self.standard_id),
            ("edition", self.edition),
            ("dataset_version", self.dataset_version),
            ("reference_snapshot_id", self.reference_snapshot_id),
        ):
            if not value:
                raise PolicyError(f"reference {name} must be non-empty")


@dataclass(frozen=True, slots=True)
class AccountingPolicySet:
    """Versioned aggregate root of the policies bounded context."""

    policy_set_id: str
    accounting_entity_id: EntityId
    code: str
    version: str
    reference: PolicySetReference
    status: PolicySetStatus = PolicySetStatus.DRAFT
    effective_from: date | None = None
    effective_to: date | None = None
    parent_policy_set_id: str | None = None
    bindings: tuple[PolicyBinding, ...] = ()

    def __post_init__(self) -> None:
        if not self.policy_set_id:
            raise PolicyError("policy_set_id must be non-empty")
        if not self.code:
            raise PolicyError("code must be non-empty")
        if not self.version:
            raise PolicyError("version must be non-empty")
        if self.effective_to is not None and self.effective_from is not None:
            if self.effective_to < self.effective_from:
                raise PolicyError("effective_to precedes effective_from (INV-POLSET-003)")

    @property
    def is_modifiable(self) -> bool:
        """Bindings may only change while the set is a draft."""
        return self.status is PolicySetStatus.DRAFT

    def with_binding(self, binding: PolicyBinding) -> AccountingPolicySet:
        """Add one pinned binding; mutating a non-draft set is rejected."""
        if not self.is_modifiable:
            raise PolicyError(f"policy set {self.code!r} is {self.status.value}, not modifiable")
        same_type = [
            existing for existing in self.bindings if existing.policy_type is binding.policy_type
        ]
        for existing in same_type:
            if existing.policy_id == binding.policy_id:
                raise PolicyError(
                    f"binding on {binding.policy_type.value} {binding.policy_id!r} already set"
                )
        return AccountingPolicySet(
            policy_set_id=self.policy_set_id,
            accounting_entity_id=self.accounting_entity_id,
            code=self.code,
            version=self.version,
            reference=self.reference,
            status=self.status,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            parent_policy_set_id=self.parent_policy_set_id,
            bindings=(*self.bindings, binding),
        )

    def activate(self, effective_from: date) -> AccountingPolicySet:
        """Move a DRAFT set to ACTIVE (INV-POLSET-002 keeps versions stable)."""
        if self.status is not PolicySetStatus.DRAFT:
            raise PolicyError(
                f"policy set {self.code!r} cannot be activated from {self.status.value}"
            )
        return AccountingPolicySet(
            policy_set_id=self.policy_set_id,
            accounting_entity_id=self.accounting_entity_id,
            code=self.code,
            version=self.version,
            reference=self.reference,
            status=PolicySetStatus.ACTIVE,
            effective_from=effective_from,
            effective_to=None,
            parent_policy_set_id=self.parent_policy_set_id,
            bindings=self.bindings,
        )

    def supersede(self, effective_to: date, reason: str) -> AccountingPolicySet:
        """Supersede an ACTIVE set while preserving it for replay (ADR-POL-016)."""
        if self.status is not PolicySetStatus.ACTIVE:
            raise PolicyError(f"policy set {self.code!r} is not ACTIVE")
        if not reason:
            raise PolicyError("a supersession requires an explicit reason")
        return AccountingPolicySet(
            policy_set_id=self.policy_set_id,
            accounting_entity_id=self.accounting_entity_id,
            code=self.code,
            version=self.version,
            reference=self.reference,
            status=PolicySetStatus.SUPERSEDED,
            effective_from=self.effective_from,
            effective_to=effective_to,
            parent_policy_set_id=self.parent_policy_set_id,
            bindings=self.bindings,
        )

    def retire(self, effective_to: date, reason: str) -> AccountingPolicySet:
        """Retire an ACTIVE set entirely (spec section 10)."""
        if self.status is not PolicySetStatus.ACTIVE:
            raise PolicyError(f"policy set {self.code!r} is not ACTIVE")
        if not reason:
            raise PolicyError("a retirement requires an explicit reason")
        return AccountingPolicySet(
            policy_set_id=self.policy_set_id,
            accounting_entity_id=self.accounting_entity_id,
            code=self.code,
            version=self.version,
            reference=self.reference,
            status=PolicySetStatus.RETIRED,
            effective_from=self.effective_from,
            effective_to=effective_to,
            parent_policy_set_id=self.parent_policy_set_id,
            bindings=self.bindings,
        )

    def binding_for(self, policy_type: PolicyType) -> PolicyBinding | None:
        """Return the single binding of a policy type, if any."""
        matches = [binding for binding in self.bindings if binding.policy_type is policy_type]
        if len(matches) > 1:
            raise PolicyError(
                f"multiple {policy_type.value} bindings in {self.code!r}: ambiguous set"
            )
        return matches[0] if matches else None


__all__ = [
    "AccountingPolicySet",
    "PolicyBinding",
    "PolicySetReference",
    "PolicySetStatus",
    "PolicyType",
]
