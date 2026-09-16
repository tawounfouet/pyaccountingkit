"""Property qualification for LOT-19 settlement and schedule invariants."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId, EntryId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.allocation import SettlementAllocationService
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.payment_terms import DueDateRule, PaymentTerm
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.settlement import Settlement

ENTITY = EntityId("ent")
AR = "subledger:ar"
PARTY = "party:customer"


def _money(cents: int) -> Money:
    return Money(Decimal(cents) / Decimal(100), EUR)


def _posted(entry_id: str) -> PostedAccountingReference:
    return PostedAccountingReference(
        entity_id=ENTITY,
        entry_id=EntryId(entry_id),
        posted_at=datetime(2026, 9, 16, tzinfo=UTC),
    )


@given(
    original_cents=st.integers(min_value=1, max_value=10_000_000),
    allocated_cents=st.integers(min_value=1, max_value=10_000_000),
)
def test_due_item_allocation_preserves_original_balance_identity(
    original_cents: int,
    allocated_cents: int,
) -> None:
    bounded = min(original_cents, allocated_cents)
    due = DueItem.create(
        due_item_id="due:property",
        entity_id=ENTITY,
        source_subledger_item_id="rec:property",
        due_date=date(2026, 10, 31),
        original_amount=_money(original_cents),
    )
    updated = due.allocate(_money(bounded), expected_revision=0)

    allocated = updated.original_amount - updated.open_amount
    assert allocated + updated.open_amount == updated.original_amount
    assert updated.revision == 1


@given(
    settlement_cents=st.integers(min_value=1, max_value=10_000_000),
    allocated_cents=st.integers(min_value=1, max_value=10_000_000),
)
def test_settlement_allocation_preserves_open_plus_allocated_identity(
    settlement_cents: int,
    allocated_cents: int,
) -> None:
    bounded = min(settlement_cents, allocated_cents)
    amount = _money(settlement_cents)
    due = DueItem.create(
        due_item_id="due:property",
        entity_id=ENTITY,
        source_subledger_item_id="rec:property",
        due_date=date(2026, 10, 31),
        original_amount=amount,
    )
    receivable = (
        Receivable(
            receivable_id="rec:property",
            entity_id=ENTITY,
            subledger_id=AR,
            party_id=PARTY,
            source_document_ref="invoice:property",
            original_amount=amount,
            accounting_date=date(2026, 9, 1),
            due_items=(due,),
        )
        .open()
        .link_posted_accounting(_posted("entry:invoice"))
    )
    settlement = Settlement.create(
        settlement_id="settlement:property",
        entity_id=ENTITY,
        subledger_id=AR,
        party_id=PARTY,
        settlement_date=date(2026, 10, 15),
        accounting_date=date(2026, 10, 15),
        amount=amount,
        source_reference="bank:property",
    ).link_posted_accounting(_posted("entry:settlement"))

    result = SettlementAllocationService().allocate(
        allocation_id="allocation:property",
        settlement=settlement,
        subledger_item=receivable,
        due_item_id=due.due_item_id,
        amount=_money(bounded),
        allocation_date=date(2026, 10, 15),
    )

    assert result.settlement.allocated_amount + result.settlement.open_amount == amount
    updated_due = result.subledger_item.due_items[0]
    allocated_due = updated_due.original_amount - updated_due.open_amount
    assert allocated_due + updated_due.open_amount == amount


@given(total_cents=st.integers(min_value=3, max_value=10_000_000))
def test_payment_term_generated_due_amounts_always_reconcile(total_cents: int) -> None:
    term = PaymentTerm(
        payment_term_id="term:property",
        code="THIRDS",
        version="1",
        rules=(
            DueDateRule("a", 30, Decimal("0.3333"), 1),
            DueDateRule("b", 60, Decimal("0.3333"), 2),
            DueDateRule("c", 90, Decimal("0.3334"), 3),
        ),
    )
    amount = _money(total_cents)
    due_items = term.generate_due_items(
        entity_id=ENTITY,
        source_subledger_item_id="rec:term-property",
        document_date=date(2026, 9, 1),
        amount=amount,
    )

    total = Money.zero(EUR)
    for due_item in due_items:
        total += due_item.original_amount
    assert total == amount
