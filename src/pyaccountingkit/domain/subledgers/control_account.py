"""Explicit control-account bindings and resolution results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.identifiers import AccountId, EntityId
from pyaccountingkit.domain.subledgers.errors import InvalidSubledgerConfigurationError
from pyaccountingkit.domain.subledgers.primitives import BindingStatus, SubledgerPartyType


@dataclass(frozen=True, slots=True)
class ControlAccountBinding:
    binding_id: str
    entity_id: EntityId
    subledger_id: str
    company_account_id: AccountId
    effective_from: date
    effective_to: date | None = None
    party_type: SubledgerPartyType | None = None
    currency: Currency | None = None
    status: BindingStatus = BindingStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.binding_id.strip():
            raise InvalidSubledgerConfigurationError("binding_id must not be empty")
        if not self.subledger_id.strip():
            raise InvalidSubledgerConfigurationError("binding subledger_id must not be empty")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise InvalidSubledgerConfigurationError(
                "control-account binding effective_to must be after effective_from"
            )

    def effective_on(self, accounting_date: date) -> bool:
        return self.effective_from <= accounting_date and (
            self.effective_to is None or accounting_date < self.effective_to
        )

    def matches(
        self,
        *,
        entity_id: EntityId,
        subledger_id: str,
        accounting_date: date,
        party_type: SubledgerPartyType | None,
        currency: Currency | None,
    ) -> bool:
        if self.status is not BindingStatus.ACTIVE:
            return False
        if self.entity_id != entity_id or self.subledger_id != subledger_id:
            return False
        if not self.effective_on(accounting_date):
            return False
        if self.party_type is not None and self.party_type != party_type:
            return False
        if self.currency is not None and self.currency != currency:
            return False
        return True

    def specificity(self) -> int:
        return int(self.party_type is not None) + int(self.currency is not None)


@dataclass(frozen=True, slots=True)
class ResolvedControlAccount:
    binding_id: str
    account_id: AccountId
    account_code: str
    entity_id: EntityId
    subledger_id: str
    chart_id: str
    chart_version: str
    reference_snapshot_id: str


__all__ = ["ControlAccountBinding", "ResolvedControlAccount"]
