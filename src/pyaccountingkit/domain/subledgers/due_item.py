"""Due items for receivable/payable schedules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.errors import InvalidDueItemError


@dataclass(frozen=True, slots=True)
class DueItem:
    due_item_id: str
    entity_id: EntityId
    source_subledger_item_id: str
    due_date: date
    original_amount: Money
    open_amount: Money

    def __post_init__(self) -> None:
        if not self.due_item_id.strip():
            raise InvalidDueItemError("due_item_id must not be empty")
        if not self.source_subledger_item_id.strip():
            raise InvalidDueItemError("source_subledger_item_id must not be empty")
        if self.original_amount.amount <= 0:
            raise InvalidDueItemError("due item original amount must be strictly positive")
        if self.open_amount.currency != self.original_amount.currency:
            raise InvalidDueItemError("due item open/original currencies must match")
        if self.open_amount != self.original_amount:
            raise InvalidDueItemError(
                "LOT-18 due items must start fully open; settlement changes belong to LOT-19"
            )

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


__all__ = ["DueItem"]
