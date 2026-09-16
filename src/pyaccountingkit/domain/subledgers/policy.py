"""Versioned auxiliary-accounting policy for subledger foundations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.subledgers.auxiliary import AuxiliaryReference
from pyaccountingkit.domain.subledgers.errors import (
    AuxiliaryPolicyNotActiveError,
    AuxiliaryPolicyNotEffectiveError,
    InvalidSubledgerConfigurationError,
)
from pyaccountingkit.domain.subledgers.primitives import (
    AuxiliaryMode,
    AuxiliaryPolicyStatus,
)


@dataclass(frozen=True, slots=True)
class AuxiliaryAccountingPolicy:
    policy_id: str
    entity_id: EntityId
    subledger_id: str
    version: str
    auxiliary_mode: AuxiliaryMode
    status: AuxiliaryPolicyStatus
    effective_from: date
    effective_to: date | None = None
    require_auxiliary_reference: bool = False

    def __post_init__(self) -> None:
        for name in ("policy_id", "subledger_id", "version"):
            if not getattr(self, name).strip():
                raise InvalidSubledgerConfigurationError(f"{name} must not be empty")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise InvalidSubledgerConfigurationError(
                "auxiliary policy effective_to must be after effective_from"
            )

    def effective_on(self, accounting_date: date) -> bool:
        return self.effective_from <= accounting_date and (
            self.effective_to is None or accounting_date < self.effective_to
        )

    def assert_executable(
        self,
        *,
        entity_id: EntityId,
        subledger_id: str,
        accounting_date: date,
        auxiliary_reference: AuxiliaryReference | None = None,
    ) -> None:
        require_same_entity(self.entity_id, entity_id, resource="auxiliary accounting policy")
        if subledger_id != self.subledger_id:
            raise InvalidSubledgerConfigurationError(
                f"policy {self.policy_id!r} targets subledger {self.subledger_id!r}, "
                f"not {subledger_id!r}"
            )
        if self.status is not AuxiliaryPolicyStatus.ACTIVE:
            raise AuxiliaryPolicyNotActiveError(
                f"auxiliary policy {self.policy_id!r} is {self.status.value}"
            )
        if not self.effective_on(accounting_date):
            raise AuxiliaryPolicyNotEffectiveError(
                f"auxiliary policy {self.policy_id!r} is not effective on {accounting_date}"
            )
        if self.require_auxiliary_reference and auxiliary_reference is None:
            raise InvalidSubledgerConfigurationError(
                f"auxiliary policy {self.policy_id!r} requires an auxiliary reference"
            )


__all__ = ["AuxiliaryAccountingPolicy"]
