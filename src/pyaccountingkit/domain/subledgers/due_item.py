"""Due items for receivable/payable schedules and immutable allocation transitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.errors import (
    AllocationConcurrencyConflictError,
    DueItemOverAllocationError,
    InvalidDueItemError,
)


@dataclass(frozen=True, slots=True)
class DueItem:
    due_item_id: str
    entity_id: EntityId
    source_subledger_item_id: str
    due_date: date
    original_amount: Money
    open_amount: Money
    revision: int = 0

    def __post_init__(self) -> None:
        if not self.due_item_id.strip():
            raise InvalidDueItemError("due_item_id must not be empty")
        if not self.source_subledger_item_id.strip():
            raise InvalidDueItemError("source_subledger_item_id must not be empty")
        if self.original_amount.amount <= 0:
            raise InvalidDueItemError("due item original amount must be strictly positive")
        if self.open_amount.currency != self.original_amount.currency:
            raise InvalidDueItemError("due item open/original currencies must match")
        if self.open_amount.amount < 0:
            raise InvalidDueItemError("due item open amount cannot be negative")
        if self.open_amount.compare(self.original_amount) > 0:
            raise InvalidDueItemError("due item open amount cannot exceed original amount")
        if self.revision < 0:
            raise InvalidDueItemError("due item revision cannot be negative")
        if self.revision == 0 and self.open_amount != self.original_amount:
            raise InvalidDueItemError(
                "new due items must start fully open; partial state requires an allocation transition"
            )

    @property
    def is_settled(self) -> bool:
        return self.open_amount.is_zero()

    @property
    def is_partially_settled(self) -> bool:
        return not self.open_amount.is_zero() and self.open_amount != self.original_amount

    @classmethod
    def create(
        cls,
        *,
        due_item_id: str,
        entity_id: EntityId,
        source_subledger_item_id: str,
        due_date: date,
        original_amount: Money,
    ) -> DueItem:
        return cls(
            due_item_id=due_item_id,
            entity_id=entity_id,
            source_subledger_item_id=source_subledger_item_id,
            due_date=due_date,
            original_amount=original_amount,
            open_amount=original_amount,
        )

    def allocate(self, amount: Money, *, expected_revision: int | None = None) -> DueItem:
        self._check_revision(expected_revision)
        self._check_transition_amount(amount)
        if amount.compare(self.open_amount) > 0:
            raise DueItemOverAllocationError(
                f"allocation {amount} exceeds due-item open amount {self.open_amount}"
            )
        return replace(
            self,
            open_amount=self.open_amount - amount,
            revision=self.revision + 1,
        )

    def restore(self, amount: Money, *, expected_revision: int | None = None) -> DueItem:
        self._check_revision(expected_revision)
        self._check_transition_amount(amount)
        restored = self.open_amount + amount
        if restored.compare(self.original_amount) > 0:
            raise InvalidDueItemError(
                f"restored open amount {restored} exceeds original amount {self.original_amount}"
            )
        return replace(self, open_amount=restored, revision=self.revision + 1)

    def _check_revision(self, expected_revision: int | None) -> None:
        if expected_revision is not None and expected_revision != self.revision:
            raise AllocationConcurrencyConflictError(
                f"due item {self.due_item_id!r} revision {self.revision} "
                f"does not match expected revision {expected_revision}"
            )

    def _check_transition_amount(self, amount: Money) -> None:
        if amount.currency != self.original_amount.currency:
            raise InvalidDueItemError("allocation/restoration currency must match due item currency")
        if amount.amount <= 0:
            raise InvalidDueItemError("allocation/restoration amount must be strictly positive")


__all__ = ["DueItem"]
