"""Golden LOT-19 scenarios for settlement, aging and reconciliation."""

from __future__ import annotations

from datetime import UTC, date, datetime

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import AccountId, EntityId, EntryId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.aging import (
    AgingBucketDefinition,
    AgingDateBasis,
    AgingEngine,
    AgingPolicy,
    AgingSourceItem,
)
from pyaccountingkit.domain.subledgers.allocation import SettlementAllocationService
from pyaccountingkit.domain.subledgers.control_account import ResolvedControlAccount
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.open_item import OpenItem
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.reconciliation import (
    SubledgerReconciliationService,
    SubledgerReconciliationStatus,
)
from pyaccountingkit.domain.subledgers.settlement import Settlement

ENTITY = EntityId("golden-entity")
AR = "subledger:ar"
PARTY = "party:golden-customer"


def _money(value: str) -> Money:
    return Money.from_str(value, EUR)


def _posted(entry_id: str) -> PostedAccountingReference:
    return PostedAccountingReference(
        entity_id=ENTITY,
        entry_id=EntryId(entry_id),
        posted_at=datetime(2026, 9, 16, tzinfo=UTC),
    )


def _invoice() -> Receivable:
    due_1 = DueItem.create(
        due_item_id="due:1",
        entity_id=ENTITY,
        source_subledger_item_id="invoice:1200",
        due_date=date(2026, 10, 31),
        original_amount=_money("600.00"),
    )
    due_2 = DueItem.create(
        due_item_id="due:2",
        entity_id=ENTITY,
        source_subledger_item_id="invoice:1200",
        due_date=date(2026, 11, 30),
        original_amount=_money("600.00"),
    )
    return (
        Receivable(
            receivable_id="invoice:1200",
            entity_id=ENTITY,
            subledger_id=AR,
            party_id=PARTY,
            source_document_ref="INV-1200",
            original_amount=_money("1200.00"),
            accounting_date=date(2026, 9, 1),
            due_items=(due_1, due_2),
        )
        .open()
        .link_posted_accounting(_posted("entry:invoice-1200"))
    )


def _settlement(settlement_id: str, amount: str) -> Settlement:
    return Settlement.create(
        settlement_id=settlement_id,
        entity_id=ENTITY,
        subledger_id=AR,
        party_id=PARTY,
        settlement_date=date(2026, 10, 15),
        accounting_date=date(2026, 10, 15),
        amount=_money(amount),
        source_reference=f"BANK-{settlement_id}",
    ).link_posted_accounting(_posted(f"entry:{settlement_id}"))


def _aging_policy() -> AgingPolicy:
    return AgingPolicy(
        policy_id="aging:golden",
        version="1",
        date_basis=AgingDateBasis.DUE_DATE,
        buckets=(
            AgingBucketDefinition("CURRENT", None, 0),
            AgingBucketDefinition("1_30", 1, 30),
            AgingBucketDefinition("31_60", 31, 60),
            AgingBucketDefinition("61_PLUS", 61, None),
        ),
    )


def _control_account() -> ResolvedControlAccount:
    return ResolvedControlAccount(
        binding_id="binding:ar",
        account_id=AccountId("account:411000"),
        account_code="411000",
        entity_id=ENTITY,
        subledger_id=AR,
        chart_id="chart:pcg",
        chart_version="2026",
        reference_snapshot_id="snapshot:pcg:2026",
    )


def test_golden_invoice_1200_settlement_500_ages_and_reconciles_to_700() -> None:
    allocation = SettlementAllocationService().allocate(
        allocation_id="allocation:500",
        settlement=_settlement("settlement:500", "500.00"),
        subledger_item=_invoice(),
        due_item_id="due:1",
        amount=_money("500.00"),
        allocation_date=date(2026, 10, 15),
    )
    invoice = allocation.subledger_item

    assert allocation.settlement.open_amount.is_zero()
    assert invoice.due_items[0].open_amount == _money("100.00")
    assert invoice.due_items[1].open_amount == _money("600.00")
    assert invoice.open_amount == _money("700.00")

    aging_sources = tuple(AgingSourceItem.from_receivable(invoice, due) for due in invoice.due_items)
    aging = AgingEngine().snapshot(
        entity_id=ENTITY,
        subledger_id=AR,
        as_of=date(2026, 12, 31),
        currency=EUR,
        policy=_aging_policy(),
        sources=aging_sources,
    )
    bucket_totals = {bucket.bucket_id: bucket.total for bucket in aging.buckets}
    assert aging.total_open == _money("700.00")
    assert bucket_totals == {
        "CURRENT": _money("0.00"),
        "1_30": _money("0.00"),
        "31_60": _money("600.00"),
        "61_PLUS": _money("100.00"),
    }

    open_items = tuple(
        OpenItem.from_receivable(
            open_item_id=f"open:{due.due_item_id}",
            receivable=invoice,
            due_item=due,
        )
        for due in invoice.due_items
    )
    reconciliation = SubledgerReconciliationService().reconcile(
        entity_id=ENTITY,
        subledger_id=AR,
        as_of=date(2026, 12, 31),
        currency=EUR,
        control_account=_control_account(),
        open_items=open_items,
        normalized_gl_balance=_money("700.00"),
    )
    assert reconciliation.status is SubledgerReconciliationStatus.MATCHED
    assert reconciliation.subledger_open_balance == _money("700.00")
    assert reconciliation.difference.is_zero()


def test_golden_overpayment_keeps_unapplied_settlement_amount_explicit() -> None:
    allocation = SettlementAllocationService().allocate(
        allocation_id="allocation:overpayment",
        settlement=_settlement("settlement:overpayment", "1500.00"),
        subledger_item=_invoice(),
        due_item_id="due:1",
        amount=_money("600.00"),
        allocation_date=date(2026, 10, 15),
    )

    assert allocation.settlement.open_amount == _money("900.00")
    assert allocation.settlement.allocated_amount == _money("600.00")
    assert allocation.subledger_item.open_amount == _money("600.00")
