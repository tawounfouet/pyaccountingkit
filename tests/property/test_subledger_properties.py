"""Property qualification for LOT-18 subledger foundations."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.receivable import Receivable

ENTITY = EntityId("ent")


def _euros(cents: int) -> Money:
    return Money(Decimal(cents) / Decimal(100), EUR)


@given(
    first_cents=st.integers(min_value=1, max_value=10_000_000),
    second_cents=st.integers(min_value=1, max_value=10_000_000),
)
def test_due_schedule_partition_reconciles_to_receivable(
    first_cents: int,
    second_cents: int,
) -> None:
    receivable_id = "rec:property"
    first = DueItem.create(
        due_item_id="due:first",
        entity_id=ENTITY,
        source_subledger_item_id=receivable_id,
        due_date=date(2026, 10, 31),
        original_amount=_euros(first_cents),
    )
    second = DueItem.create(
        due_item_id="due:second",
        entity_id=ENTITY,
        source_subledger_item_id=receivable_id,
        due_date=date(2026, 11, 30),
        original_amount=_euros(second_cents),
    )
    total = _euros(first_cents + second_cents)

    receivable = Receivable(
        receivable_id=receivable_id,
        entity_id=ENTITY,
        subledger_id="subledger:ar",
        party_id="party:customer",
        source_document_ref="invoice:property",
        original_amount=total,
        accounting_date=date(2026, 9, 16),
        due_items=(first, second),
    )

    reconstructed = Money.zero(EUR)
    for due_item in receivable.due_items:
        reconstructed += due_item.original_amount

    assert reconstructed == receivable.original_amount
    assert all(due.open_amount == due.original_amount for due in receivable.due_items)
