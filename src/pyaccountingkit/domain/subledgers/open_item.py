"""Open-item projection distinct from General Ledger journal lines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.errors import InvalidSubledgerItemError
from pyaccountingkit.domain.subledgers.primitives import AccountingEffectStatus

if TYPE_CHECKING:
    from pyaccountingkit.domain.subledgers.payable import Payable
    from pyaccountingkit.domain.subledgers.receivable import Receivable


@dataclass(frozen=True, slots=True)
class OpenItem:
    open_item_id: str
    entity_id: EntityId
    subledger_id: str
    party_id: str
    source_item_id: str
    due_item_id: str
    due_date: date
    original_amount: Money
    open_amount: Money
    accounting_reference: PostedAccountingReference

    def __post_init__(self) -> None:
        for name in ("open_item_id", "subledger_id", "party_id", "source_item_id", "due_item_id"):
            if not getattr(self, name).strip():
                raise InvalidSubledgerItemError(f"{name} must not be empty")
        require_same_entity(
            self.entity_id,
            self.accounting_reference.entity_id,
            resource="open-item posted accounting reference",
        )
        if self.open_amount.currency != self.original_amount.currency:
            raise InvalidSubledgerItemError("open-item currencies must match")
        if self.open_amount.amount <= 0 or self.open_amount.compare(self.original_amount) > 0:
            raise InvalidSubledgerItemError(
                "open-item amount must be positive and no greater than original amount"
            )

    @classmethod
    def from_receivable(
        cls,
        *,
        open_item_id: str,
        receivable: Receivable,
        due_item: DueItem,
    ) -> OpenItem:
        return cls._from_parent(
            open_item_id=open_item_id,
            item_id=receivable.receivable_id,
            entity_id=receivable.entity_id,
            subledger_id=receivable.subledger_id,
            party_id=receivable.party_id,
            accounting_status=receivable.accounting_status,
            accounting_reference=receivable.accounting_reference,
            due_items=receivable.due_items,
            due_item=due_item,
        )

    @classmethod
    def from_payable(
        cls,
        *,
        open_item_id: str,
        payable: Payable,
        due_item: DueItem,
    ) -> OpenItem:
        return cls._from_parent(
            open_item_id=open_item_id,
            item_id=payable.payable_id,
            entity_id=payable.entity_id,
            subledger_id=payable.subledger_id,
            party_id=payable.party_id,
            accounting_status=payable.accounting_status,
            accounting_reference=payable.accounting_reference,
            due_items=payable.due_items,
            due_item=due_item,
        )

    @classmethod
    def _from_parent(
        cls,
        *,
        open_item_id: str,
        item_id: str,
        entity_id: EntityId,
        subledger_id: str,
        party_id: str,
        accounting_status: AccountingEffectStatus,
        accounting_reference: PostedAccountingReference | None,
        due_items: tuple[DueItem, ...],
        due_item: DueItem,
    ) -> OpenItem:
        if accounting_status is not AccountingEffectStatus.POSTED or accounting_reference is None:
            raise InvalidSubledgerItemError(
                "open items can only be created from accounting-effective subledger items"
            )
        if due_item not in due_items or due_item.source_subledger_item_id != item_id:
            raise InvalidSubledgerItemError("due item does not belong to the requested parent")
        require_same_entity(entity_id, due_item.entity_id, resource=f"due item {due_item.due_item_id}")
        return cls(
            open_item_id=open_item_id,
            entity_id=entity_id,
            subledger_id=subledger_id,
            party_id=party_id,
            source_item_id=item_id,
            due_item_id=due_item.due_item_id,
            due_date=due_item.due_date,
            original_amount=due_item.original_amount,
            open_amount=due_item.open_amount,
            accounting_reference=accounting_reference,
        )


__all__ = ["OpenItem"]
