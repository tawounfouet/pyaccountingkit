"""Receivable aggregate root for LOT-18 subledger foundations."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers._item import validate_item
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.errors import InvalidSubledgerItemError
from pyaccountingkit.domain.subledgers.primitives import (
    AccountingEffectStatus,
    OperationalItemStatus,
)


@dataclass(frozen=True, slots=True)
class Receivable:
    receivable_id: str
    entity_id: EntityId
    subledger_id: str
    party_id: str
    source_document_ref: str
    original_amount: Money
    accounting_date: date
    due_items: tuple[DueItem, ...]
    operational_status: OperationalItemStatus = OperationalItemStatus.DRAFT
    accounting_status: AccountingEffectStatus = AccountingEffectStatus.PENDING
    accounting_reference: PostedAccountingReference | None = None

    def __post_init__(self) -> None:
        validate_item(
            item_id=self.receivable_id,
            entity_id=self.entity_id,
            subledger_id=self.subledger_id,
            party_id=self.party_id,
            source_document_ref=self.source_document_ref,
            original_amount=self.original_amount,
            due_items=self.due_items,
            accounting_status=self.accounting_status,
            accounting_reference=self.accounting_reference,
        )

    @property
    def accounting_effective(self) -> bool:
        return self.accounting_status is AccountingEffectStatus.POSTED

    def open(self) -> Receivable:
        if self.operational_status is not OperationalItemStatus.DRAFT:
            raise InvalidSubledgerItemError("only a DRAFT receivable can become OPEN")
        return replace(self, operational_status=OperationalItemStatus.OPEN)

    def link_posted_accounting(self, reference: PostedAccountingReference) -> Receivable:
        if self.accounting_status is not AccountingEffectStatus.PENDING:
            raise InvalidSubledgerItemError(
                "only a PENDING receivable can link its posted accounting effect"
            )
        require_same_entity(
            self.entity_id,
            reference.entity_id,
            resource="receivable posted accounting reference",
        )
        return replace(
            self,
            accounting_status=AccountingEffectStatus.POSTED,
            accounting_reference=reference,
        )


__all__ = ["Receivable"]
