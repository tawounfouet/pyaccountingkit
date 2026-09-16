"""Shared invariants for receivable and payable roots."""

from __future__ import annotations

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.errors import InvalidSubledgerItemError
from pyaccountingkit.domain.subledgers.primitives import AccountingEffectStatus


def validate_item(
    *,
    item_id: str,
    entity_id: EntityId,
    subledger_id: str,
    party_id: str,
    source_document_ref: str,
    original_amount: Money,
    due_items: tuple[DueItem, ...],
    accounting_status: AccountingEffectStatus,
    accounting_reference: PostedAccountingReference | None,
) -> None:
    for name, value in (
        ("item_id", item_id),
        ("subledger_id", subledger_id),
        ("party_id", party_id),
        ("source_document_ref", source_document_ref),
    ):
        if not value.strip():
            raise InvalidSubledgerItemError(f"{name} must not be empty")
    if original_amount.amount <= 0:
        raise InvalidSubledgerItemError("subledger original amount must be strictly positive")
    if not due_items:
        raise InvalidSubledgerItemError("subledger item requires at least one due item")

    total = Money.zero(original_amount.currency)
    for due_item in due_items:
        require_same_entity(
            entity_id,
            due_item.entity_id,
            resource=f"due item {due_item.due_item_id}",
        )
        if due_item.source_subledger_item_id != item_id:
            raise InvalidSubledgerItemError(
                f"due item {due_item.due_item_id!r} targets a different parent item"
            )
        if due_item.original_amount.currency != original_amount.currency:
            raise InvalidSubledgerItemError("all due items must use the parent item currency")
        total += due_item.original_amount
    if total != original_amount:
        raise InvalidSubledgerItemError(
            "sum(due_item.original_amount) must equal the receivable/payable original amount"
        )

    if accounting_status is AccountingEffectStatus.PENDING and accounting_reference is not None:
        raise InvalidSubledgerItemError("PENDING accounting effect cannot carry a posted reference")
    if accounting_status is not AccountingEffectStatus.PENDING and accounting_reference is None:
        raise InvalidSubledgerItemError(
            f"{accounting_status.value} accounting effect requires a posted accounting reference"
        )
    if accounting_reference is not None:
        require_same_entity(
            entity_id,
            accounting_reference.entity_id,
            resource="posted accounting reference",
        )


__all__ = ["validate_item"]
