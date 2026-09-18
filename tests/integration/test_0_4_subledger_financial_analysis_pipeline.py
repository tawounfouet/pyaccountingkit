"""Release 0.4 cross-lot qualification for subledgers and financial analysis."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

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
from pyaccountingkit.domain.subledgers.payable import Payable
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.reconciliation import (
    SubledgerReconciliationService,
    SubledgerReconciliationStatus,
)
from pyaccountingkit.domain.subledgers.settlement import Settlement
from tests.support.financial_analysis import run_golden_analysis

ENTITY = EntityId("release-0-4-entity")
AR = "subledger:ar"
AP = "subledger:ap"
CUSTOMER = "party:customer"
SUPPLIER = "party:supplier"


def _money(value: str) -> Money:
    return Money.from_str(value, EUR)


def _posted(entry_id: str) -> PostedAccountingReference:
    return PostedAccountingReference(
        entity_id=ENTITY,
        entry_id=EntryId(entry_id),
        posted_at=datetime(2026, 9, 18, tzinfo=UTC),
    )


def _aging_policy() -> AgingPolicy:
    return AgingPolicy(
        policy_id="aging:release-0.4",
        version="1",
        date_basis=AgingDateBasis.DUE_DATE,
        buckets=(
            AgingBucketDefinition("CURRENT", None, 0),
            AgingBucketDefinition("1_30", 1, 30),
            AgingBucketDefinition("31_60", 31, 60),
            AgingBucketDefinition("61_PLUS", 61, None),
        ),
    )


def _control_account(*, subledger_id: str, account_id: str, account_code: str) -> ResolvedControlAccount:
    return ResolvedControlAccount(
        binding_id=f"binding:{subledger_id}",
        account_id=AccountId(account_id),
        account_code=account_code,
        entity_id=ENTITY,
        subledger_id=subledger_id,
        chart_id="chart:pcg",
        chart_version="2026",
        reference_snapshot_id="snapshot:pcg:2026",
    )


def _settlement(
    *,
    settlement_id: str,
    subledger_id: str,
    party_id: str,
    amount: str,
) -> Settlement:
    return Settlement.create(
        settlement_id=settlement_id,
        entity_id=ENTITY,
        subledger_id=subledger_id,
        party_id=party_id,
        settlement_date=date(2026, 10, 15),
        accounting_date=date(2026, 10, 15),
        amount=_money(amount),
        source_reference=f"BANK-{settlement_id}",
    ).link_posted_accounting(_posted(f"entry:{settlement_id}"))


def test_release_0_4_ar_ap_pipeline_reconciles_and_analysis_remains_read_only() -> None:
    ar_due = DueItem.create(
        due_item_id="due:ar",
        entity_id=ENTITY,
        source_subledger_item_id="receivable:1000",
        due_date=date(2026, 10, 31),
        original_amount=_money("1000.00"),
    )
    receivable = (
        Receivable(
            receivable_id="receivable:1000",
            entity_id=ENTITY,
            subledger_id=AR,
            party_id=CUSTOMER,
            source_document_ref="INV-1000",
            original_amount=_money("1000.00"),
            accounting_date=date(2026, 9, 1),
            due_items=(ar_due,),
        )
        .open()
        .link_posted_accounting(_posted("entry:receivable"))
    )
    ar_allocation = SettlementAllocationService().allocate(
        allocation_id="allocation:ar:400",
        settlement=_settlement(
            settlement_id="settlement:ar:400",
            subledger_id=AR,
            party_id=CUSTOMER,
            amount="400.00",
        ),
        subledger_item=receivable,
        due_item_id=ar_due.due_item_id,
        amount=_money("400.00"),
        allocation_date=date(2026, 10, 15),
    )
    receivable_after = ar_allocation.subledger_item
    ar_open = OpenItem.from_receivable(
        open_item_id="open:ar",
        receivable=receivable_after,
        due_item=receivable_after.due_items[0],
    )
    ar_aging = AgingEngine().snapshot(
        entity_id=ENTITY,
        subledger_id=AR,
        as_of=date(2026, 12, 31),
        currency=EUR,
        policy=_aging_policy(),
        sources=(AgingSourceItem.from_receivable(receivable_after, receivable_after.due_items[0]),),
    )
    ar_reconciliation = SubledgerReconciliationService().reconcile(
        entity_id=ENTITY,
        subledger_id=AR,
        as_of=date(2026, 12, 31),
        currency=EUR,
        control_account=_control_account(
            subledger_id=AR,
            account_id="account:411000",
            account_code="411000",
        ),
        open_items=(ar_open,),
        normalized_gl_balance=_money("600.00"),
    )

    ap_due = DueItem.create(
        due_item_id="due:ap",
        entity_id=ENTITY,
        source_subledger_item_id="payable:900",
        due_date=date(2026, 11, 30),
        original_amount=_money("900.00"),
    )
    payable = (
        Payable(
            payable_id="payable:900",
            entity_id=ENTITY,
            subledger_id=AP,
            party_id=SUPPLIER,
            source_document_ref="BILL-900",
            original_amount=_money("900.00"),
            accounting_date=date(2026, 9, 5),
            due_items=(ap_due,),
        )
        .open()
        .link_posted_accounting(_posted("entry:payable"))
    )
    ap_allocation = SettlementAllocationService().allocate(
        allocation_id="allocation:ap:300",
        settlement=_settlement(
            settlement_id="settlement:ap:300",
            subledger_id=AP,
            party_id=SUPPLIER,
            amount="300.00",
        ),
        subledger_item=payable,
        due_item_id=ap_due.due_item_id,
        amount=_money("300.00"),
        allocation_date=date(2026, 10, 15),
    )
    payable_after = ap_allocation.subledger_item
    ap_open = OpenItem.from_payable(
        open_item_id="open:ap",
        payable=payable_after,
        due_item=payable_after.due_items[0],
    )
    ap_aging = AgingEngine().snapshot(
        entity_id=ENTITY,
        subledger_id=AP,
        as_of=date(2026, 12, 31),
        currency=EUR,
        policy=_aging_policy(),
        sources=(AgingSourceItem.from_payable(payable_after, payable_after.due_items[0]),),
    )
    ap_reconciliation = SubledgerReconciliationService().reconcile(
        entity_id=ENTITY,
        subledger_id=AP,
        as_of=date(2026, 12, 31),
        currency=EUR,
        control_account=_control_account(
            subledger_id=AP,
            account_id="account:401000",
            account_code="401000",
        ),
        open_items=(ap_open,),
        normalized_gl_balance=_money("600.00"),
    )

    assert receivable_after.open_amount == _money("600.00")
    assert payable_after.open_amount == _money("600.00")
    assert ar_aging.total_open == _money("600.00")
    assert ap_aging.total_open == _money("600.00")
    assert ar_reconciliation.status is SubledgerReconciliationStatus.MATCHED
    assert ap_reconciliation.status is SubledgerReconciliationStatus.MATCHED
    assert ar_reconciliation.difference.is_zero()
    assert ap_reconciliation.difference.is_zero()

    ar_state_before_analysis = (receivable_after.open_amount, ar_aging.checksum)
    ap_state_before_analysis = (payable_after.open_amount, ap_aging.checksum)

    analysis = run_golden_analysis(
        analysis_snapshot_id="analysis:release-0.4",
        generated_at=datetime(2027, 1, 2, tzinfo=UTC),
    )
    indicators = dict(analysis.indicator_values)
    ratios = dict(analysis.ratio_values)

    assert indicators["EBE"] == Decimal("350.00")
    assert indicators["EBITDA"] == Decimal("360.00")
    assert indicators["CAF"] == Decimal("230.00")
    assert analysis.frng == _money("400.00")
    assert analysis.bfr == _money("250.00")
    assert analysis.net_treasury == _money("150.00")
    assert analysis.reconciled is True
    assert ratios["NET_MARGIN"] == Decimal("20")
    assert len(analysis.analysis_snapshot.checksum) == 64

    assert ar_state_before_analysis == (receivable_after.open_amount, ar_aging.checksum)
    assert ap_state_before_analysis == (payable_after.open_amount, ap_aging.checksum)
