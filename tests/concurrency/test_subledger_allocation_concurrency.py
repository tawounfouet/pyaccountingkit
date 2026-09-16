"""Concurrency qualification for revision-guarded LOT-19 allocation transitions."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId, EntryId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.allocation import SettlementAllocationService
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.errors import AllocationConcurrencyConflictError
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.settlement import Settlement
from pyaccountingkit.domain.subledgers.settlement_reversal import SettlementReversalService

ENTITY = EntityId("ent")
AR = "subledger:ar"
PARTY = "party:customer"


def _money(value: str) -> Money:
    return Money.from_str(value, EUR)


def _posted(entry_id: str) -> PostedAccountingReference:
    return PostedAccountingReference(
        entity_id=ENTITY,
        entry_id=EntryId(entry_id),
        posted_at=datetime(2026, 9, 16, tzinfo=UTC),
    )


def _receivable() -> Receivable:
    due = DueItem.create(
        due_item_id="due:1",
        entity_id=ENTITY,
        source_subledger_item_id="rec:1",
        due_date=date(2026, 10, 31),
        original_amount=_money("600.00"),
    )
    return (
        Receivable(
            receivable_id="rec:1",
            entity_id=ENTITY,
            subledger_id=AR,
            party_id=PARTY,
            source_document_ref="invoice:1",
            original_amount=_money("600.00"),
            accounting_date=date(2026, 9, 1),
            due_items=(due,),
        )
        .open()
        .link_posted_accounting(_posted("entry:invoice"))
    )


def _settlement() -> Settlement:
    return Settlement.create(
        settlement_id="settlement:1",
        entity_id=ENTITY,
        subledger_id=AR,
        party_id=PARTY,
        settlement_date=date(2026, 10, 15),
        accounting_date=date(2026, 10, 15),
        amount=_money("600.00"),
        source_reference="bank:1",
    ).link_posted_accounting(_posted("entry:settlement"))


def test_competing_allocation_rejects_stale_settlement_revision() -> None:
    service = SettlementAllocationService()
    first = service.allocate(
        allocation_id="allocation:first",
        settlement=_settlement(),
        subledger_item=_receivable(),
        due_item_id="due:1",
        amount=_money("400.00"),
        allocation_date=date(2026, 10, 15),
        expected_settlement_revision=0,
        expected_due_item_revision=0,
    )

    with pytest.raises(AllocationConcurrencyConflictError):
        service.allocate(
            allocation_id="allocation:stale-settlement",
            settlement=first.settlement,
            subledger_item=first.subledger_item,
            due_item_id="due:1",
            amount=_money("100.00"),
            allocation_date=date(2026, 10, 15),
            expected_settlement_revision=0,
            expected_due_item_revision=1,
        )


def test_competing_allocation_rejects_stale_due_item_revision() -> None:
    service = SettlementAllocationService()
    first = service.allocate(
        allocation_id="allocation:first",
        settlement=_settlement(),
        subledger_item=_receivable(),
        due_item_id="due:1",
        amount=_money("400.00"),
        allocation_date=date(2026, 10, 15),
    )

    with pytest.raises(AllocationConcurrencyConflictError):
        service.allocate(
            allocation_id="allocation:stale-due",
            settlement=first.settlement,
            subledger_item=first.subledger_item,
            due_item_id="due:1",
            amount=_money("100.00"),
            allocation_date=date(2026, 10, 15),
            expected_settlement_revision=1,
            expected_due_item_revision=0,
        )


def test_reversal_rejects_stale_expected_state_before_restoring() -> None:
    allocation_service = SettlementAllocationService()
    allocated = allocation_service.allocate(
        allocation_id="allocation:1",
        settlement=_settlement(),
        subledger_item=_receivable(),
        due_item_id="due:1",
        amount=_money("400.00"),
        allocation_date=date(2026, 10, 15),
    )

    with pytest.raises(AllocationConcurrencyConflictError):
        SettlementReversalService(allocation_service).reverse(
            reversal_id="reversal:1",
            settlement=allocated.settlement,
            subledger_items=(allocated.subledger_item,),
            allocations=(allocated.allocation,),
            reversed_at=datetime(2026, 10, 20, tzinfo=UTC),
            accounting_reversal_reference=_posted("entry:reversal"),
            reason="cancelled payment",
            expected_settlement_revision=0,
            expected_due_item_revisions={"due:1": 1},
        )
