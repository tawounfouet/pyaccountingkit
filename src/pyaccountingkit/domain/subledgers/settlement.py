"""Settlement aggregate, distinct from allocation and General Ledger posting."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.errors import (
    AllocationConcurrencyConflictError,
    InvalidSettlementError,
    SettlementAlreadyReversedError,
    SettlementNotAccountingEffectiveError,
    SettlementOverAllocationError,
)
from pyaccountingkit.domain.subledgers.primitives import AccountingEffectStatus


class SettlementStatus(StrEnum):
    OPEN = "OPEN"
    PARTIALLY_ALLOCATED = "PARTIALLY_ALLOCATED"
    FULLY_ALLOCATED = "FULLY_ALLOCATED"
    REVERSED = "REVERSED"


@dataclass(frozen=True, slots=True)
class Settlement:
    settlement_id: str
    entity_id: EntityId
    subledger_id: str
    settlement_date: date
    accounting_date: date
    amount: Money
    open_amount: Money
    source_reference: str
    party_id: str | None = None
    status: SettlementStatus = SettlementStatus.OPEN
    accounting_status: AccountingEffectStatus = AccountingEffectStatus.PENDING
    accounting_reference: PostedAccountingReference | None = None
    reversal_accounting_reference: PostedAccountingReference | None = None
    revision: int = 0
    reversed_by_id: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("settlement_id", self.settlement_id),
            ("subledger_id", self.subledger_id),
            ("source_reference", self.source_reference),
        ):
            if not value.strip():
                raise InvalidSettlementError(f"{name} must not be empty")
        if self.party_id is not None and not self.party_id.strip():
            raise InvalidSettlementError("party_id must be non-empty when provided")
        if self.amount.amount <= 0:
            raise InvalidSettlementError("settlement amount must be strictly positive")
        if self.open_amount.currency != self.amount.currency:
            raise InvalidSettlementError("settlement open/original currencies must match")
        if self.open_amount.amount < 0 or self.open_amount.compare(self.amount) > 0:
            raise InvalidSettlementError("settlement open amount must be between zero and amount")
        if self.revision < 0:
            raise InvalidSettlementError("settlement revision cannot be negative")
        self._validate_operational_status()
        self._validate_accounting_status()

    def _validate_operational_status(self) -> None:
        if self.status is SettlementStatus.OPEN and self.open_amount != self.amount:
            raise InvalidSettlementError("OPEN settlement must be fully unallocated")
        if self.status is SettlementStatus.PARTIALLY_ALLOCATED and (
            self.open_amount.is_zero() or self.open_amount == self.amount
        ):
            raise InvalidSettlementError(
                "PARTIALLY_ALLOCATED settlement requires a non-zero residual below amount"
            )
        if self.status is SettlementStatus.FULLY_ALLOCATED and not self.open_amount.is_zero():
            raise InvalidSettlementError("FULLY_ALLOCATED settlement must have zero open amount")
        if self.status is SettlementStatus.REVERSED:
            if self.open_amount != self.amount:
                raise InvalidSettlementError("REVERSED settlement must have all allocations restored")
            if not self.reversed_by_id:
                raise InvalidSettlementError("REVERSED settlement requires reversed_by_id")
        elif self.reversed_by_id is not None:
            raise InvalidSettlementError("only REVERSED settlement can carry reversed_by_id")

    def _validate_accounting_status(self) -> None:
        if self.accounting_status is AccountingEffectStatus.PENDING:
            if self.accounting_reference is not None:
                raise InvalidSettlementError("PENDING settlement cannot carry posted accounting")
            if self.reversal_accounting_reference is not None:
                raise InvalidSettlementError("PENDING settlement cannot carry reversal accounting")
            if self.status is SettlementStatus.REVERSED:
                raise InvalidSettlementError("REVERSED settlement cannot have PENDING accounting")
            return

        if self.accounting_reference is None:
            raise InvalidSettlementError(
                f"{self.accounting_status.value} settlement requires posted accounting reference"
            )
        require_same_entity(
            self.entity_id,
            self.accounting_reference.entity_id,
            resource="settlement posted accounting reference",
        )

        if self.accounting_status is AccountingEffectStatus.POSTED:
            if self.reversal_accounting_reference is not None:
                raise InvalidSettlementError("POSTED settlement cannot carry reversal accounting")
            if self.status is SettlementStatus.REVERSED:
                raise InvalidSettlementError("REVERSED settlement requires REVERSED accounting")
            return

        if self.accounting_status is AccountingEffectStatus.REVERSED:
            if self.status is not SettlementStatus.REVERSED:
                raise InvalidSettlementError("REVERSED accounting requires REVERSED settlement")
            if self.reversal_accounting_reference is None:
                raise InvalidSettlementError(
                    "REVERSED settlement requires explicit reversal accounting reference"
                )
            require_same_entity(
                self.entity_id,
                self.reversal_accounting_reference.entity_id,
                resource="settlement reversal accounting reference",
            )
            if self.reversal_accounting_reference.entry_id == self.accounting_reference.entry_id:
                raise InvalidSettlementError(
                    "settlement reversal must reference a distinct posted journal entry"
                )

    @classmethod
    def create(
        cls,
        *,
        settlement_id: str,
        entity_id: EntityId,
        subledger_id: str,
        settlement_date: date,
        accounting_date: date,
        amount: Money,
        source_reference: str,
        party_id: str | None = None,
    ) -> Settlement:
        return cls(
            settlement_id=settlement_id,
            entity_id=entity_id,
            subledger_id=subledger_id,
            settlement_date=settlement_date,
            accounting_date=accounting_date,
            amount=amount,
            open_amount=amount,
            source_reference=source_reference,
            party_id=party_id,
        )

    @property
    def accounting_effective(self) -> bool:
        return self.accounting_status is AccountingEffectStatus.POSTED

    @property
    def allocated_amount(self) -> Money:
        return self.amount - self.open_amount

    def link_posted_accounting(self, reference: PostedAccountingReference) -> Settlement:
        if self.accounting_status is not AccountingEffectStatus.PENDING:
            raise InvalidSettlementError("only a PENDING settlement can link posted accounting")
        require_same_entity(
            self.entity_id,
            reference.entity_id,
            resource="settlement posted accounting reference",
        )
        return replace(
            self,
            accounting_status=AccountingEffectStatus.POSTED,
            accounting_reference=reference,
        )

    def allocate(self, amount: Money, *, expected_revision: int | None = None) -> Settlement:
        self._check_revision(expected_revision)
        if self.status is SettlementStatus.REVERSED:
            raise SettlementAlreadyReversedError(
                f"settlement {self.settlement_id!r} is already reversed"
            )
        if not self.accounting_effective:
            raise SettlementNotAccountingEffectiveError(
                "settlement allocation requires a posted accounting effect"
            )
        self._check_amount(amount)
        if amount.compare(self.open_amount) > 0:
            raise SettlementOverAllocationError(
                f"allocation {amount} exceeds settlement open amount {self.open_amount}"
            )
        new_open = self.open_amount - amount
        status = (
            SettlementStatus.FULLY_ALLOCATED
            if new_open.is_zero()
            else SettlementStatus.PARTIALLY_ALLOCATED
        )
        return replace(
            self,
            open_amount=new_open,
            status=status,
            revision=self.revision + 1,
        )

    def restore_allocation(
        self,
        amount: Money,
        *,
        expected_revision: int | None = None,
    ) -> Settlement:
        self._check_revision(expected_revision)
        if self.status is SettlementStatus.REVERSED:
            raise SettlementAlreadyReversedError(
                f"settlement {self.settlement_id!r} is already reversed"
            )
        self._check_amount(amount)
        restored = self.open_amount + amount
        if restored.compare(self.amount) > 0:
            raise InvalidSettlementError("restoring allocation would exceed settlement amount")
        status = (
            SettlementStatus.OPEN
            if restored == self.amount
            else SettlementStatus.PARTIALLY_ALLOCATED
        )
        return replace(self, open_amount=restored, status=status, revision=self.revision + 1)

    def mark_reversed(
        self,
        *,
        reversal_id: str,
        accounting_reversal_reference: PostedAccountingReference,
        expected_revision: int | None = None,
    ) -> Settlement:
        self._check_revision(expected_revision)
        if self.status is SettlementStatus.REVERSED:
            raise SettlementAlreadyReversedError(
                f"settlement {self.settlement_id!r} is already reversed"
            )
        if not reversal_id.strip():
            raise InvalidSettlementError("reversal_id must not be empty")
        if self.open_amount != self.amount:
            raise InvalidSettlementError("all active allocations must be restored before reversal")
        if not self.accounting_effective or self.accounting_reference is None:
            raise SettlementNotAccountingEffectiveError(
                "posted settlement accounting must be reversed explicitly"
            )
        require_same_entity(
            self.entity_id,
            accounting_reversal_reference.entity_id,
            resource="settlement reversal accounting reference",
        )
        if accounting_reversal_reference.entry_id == self.accounting_reference.entry_id:
            raise InvalidSettlementError(
                "settlement reversal must reference a distinct posted journal entry"
            )
        return replace(
            self,
            status=SettlementStatus.REVERSED,
            accounting_status=AccountingEffectStatus.REVERSED,
            reversal_accounting_reference=accounting_reversal_reference,
            revision=self.revision + 1,
            reversed_by_id=reversal_id,
        )

    def _check_revision(self, expected_revision: int | None) -> None:
        if expected_revision is not None and expected_revision != self.revision:
            raise AllocationConcurrencyConflictError(
                f"settlement {self.settlement_id!r} revision {self.revision} "
                f"does not match expected revision {expected_revision}"
            )

    def _check_amount(self, amount: Money) -> None:
        if amount.currency != self.amount.currency:
            raise InvalidSettlementError("allocation currency must match settlement currency")
        if amount.amount <= 0:
            raise InvalidSettlementError("allocation amount must be strictly positive")


__all__ = ["Settlement", "SettlementStatus"]
