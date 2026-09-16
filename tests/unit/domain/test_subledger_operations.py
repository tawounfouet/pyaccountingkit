"""Unit qualification for LOT-19 settlements, matching, aging and reconciliation."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

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
from pyaccountingkit.domain.subledgers.allocation import (
    AllocationStatus,
    SettlementAllocationService,
)
from pyaccountingkit.domain.subledgers.control_account import ResolvedControlAccount
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.errors import (
    AllocationConcurrencyConflictError,
    DueItemOverAllocationError,
    NonExecutableMatchingError,
    WriteOffPolicyRequiredError,
)
from pyaccountingkit.domain.subledgers.matching import (
    AccountingMatchItem,
    MatchSide,
    MatchingCandidate,
)
from pyaccountingkit.domain.subledgers.open_item import OpenItem
from pyaccountingkit.domain.subledgers.payment_terms import DueDateRule, PaymentTerm
from pyaccountingkit.domain.subledgers.primitives import AccountingEffectStatus
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.reconciliation import (
    SubledgerReconciliationService,
    SubledgerReconciliationStatus,
)
from pyaccountingkit.domain.subledgers.settlement import Settlement, SettlementStatus
from pyaccountingkit.domain.subledgers.settlement_reversal import SettlementReversalService
from pyaccountingkit.domain.subledgers.write_off import WriteOffAuthorization, WriteOffRequest

ENTITY = EntityId("ent")
OTHER_ENTITY = EntityId("other")
AR = "subledger:ar"
PARTY = "party:customer"


def _money(value: str) -> Money:
    return Money.from_str(value, EUR)


def _posted_reference(entry_id: str, *, entity_id: EntityId = ENTITY) -> PostedAccountingReference:
    return PostedAccountingReference(
        entity_id=entity_id,
        entry_id=EntryId(entry_id),
        posted_at=datetime(2026, 9, 16, 8, 0, tzinfo=UTC),
    )


def _receivable() -> Receivable:
    due_a = DueItem.create(
        due_item_id="due:a",
        entity_id=ENTITY,
        source_subledger_item_id="rec:1",
        due_date=date(2026, 10, 31),
        original_amount=_money("600.00"),
    )
    due_b = DueItem.create(
        due_item_id="due:b",
        entity_id=ENTITY,
        source_subledger_item_id="rec:1",
        due_date=date(2026, 11, 30),
        original_amount=_money("600.00"),
    )
    return (
        Receivable(
            receivable_id="rec:1",
            entity_id=ENTITY,
            subledger_id=AR,
            party_id=PARTY,
            source_document_ref="invoice:1",
            original_amount=_money("1200.00"),
            accounting_date=date(2026, 9, 1),
            due_items=(due_a, due_b),
        )
        .open()
        .link_posted_accounting(_posted_reference("entry:invoice"))
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
        source_reference=f"bank:{settlement_id}",
    ).link_posted_accounting(_posted_reference(f"entry:{settlement_id}"))


def _match_item(item_id: str, side: MatchSide, amount: str) -> AccountingMatchItem:
    return AccountingMatchItem(
        item_id=item_id,
        entity_id=ENTITY,
        subledger_id=AR,
        party_id=PARTY,
        side=side,
        amount=_money(amount),
        accounting_reference=_posted_reference(f"entry:{item_id}"),
    )


def _aging_policy() -> AgingPolicy:
    return AgingPolicy(
        policy_id="aging:standard",
        version="1",
        date_basis=AgingDateBasis.DUE_DATE,
        buckets=(
            AgingBucketDefinition("CURRENT", None, 0),
            AgingBucketDefinition("1_30", 1, 30),
            AgingBucketDefinition("31_60", 31, 60),
            AgingBucketDefinition("61_PLUS", 61, None),
        ),
    )


def test_partial_and_full_allocation_update_immutable_balances() -> None:
    service = SettlementAllocationService()
    receivable = _receivable()
    settlement = _settlement("settlement:1", "800.00")

    first = service.allocate(
        allocation_id="allocation:1",
        settlement=settlement,
        subledger_item=receivable,
        due_item_id="due:a",
        amount=_money("500.00"),
        allocation_date=date(2026, 10, 15),
        expected_settlement_revision=0,
        expected_due_item_revision=0,
    )
    assert first.settlement.status is SettlementStatus.PARTIALLY_ALLOCATED
    assert first.settlement.open_amount == _money("300.00")
    assert first.subledger_item.open_amount == _money("700.00")

    second = service.allocate(
        allocation_id="allocation:2",
        settlement=first.settlement,
        subledger_item=first.subledger_item,
        due_item_id="due:b",
        amount=_money("300.00"),
        allocation_date=date(2026, 10, 15),
        expected_settlement_revision=1,
        expected_due_item_revision=0,
    )
    assert second.settlement.status is SettlementStatus.FULLY_ALLOCATED
    assert second.settlement.open_amount.is_zero()
    assert second.subledger_item.open_amount == _money("400.00")


def test_multiple_settlements_can_allocate_to_one_due_item() -> None:
    service = SettlementAllocationService()
    receivable = _receivable()

    first = service.allocate(
        allocation_id="allocation:first",
        settlement=_settlement("settlement:first", "400.00"),
        subledger_item=receivable,
        due_item_id="due:a",
        amount=_money("400.00"),
        allocation_date=date(2026, 10, 15),
    )
    second = service.allocate(
        allocation_id="allocation:second",
        settlement=_settlement("settlement:second", "200.00"),
        subledger_item=first.subledger_item,
        due_item_id="due:a",
        amount=_money("200.00"),
        allocation_date=date(2026, 10, 16),
        expected_due_item_revision=1,
    )

    assert second.subledger_item.due_items[0].is_settled
    assert second.subledger_item.open_amount == _money("600.00")


def test_due_item_over_allocation_and_stale_revision_fail_closed() -> None:
    service = SettlementAllocationService()
    receivable = _receivable()
    with pytest.raises(DueItemOverAllocationError):
        service.allocate(
            allocation_id="allocation:too-much",
            settlement=_settlement("settlement:large", "1000.00"),
            subledger_item=receivable,
            due_item_id="due:a",
            amount=_money("700.00"),
            allocation_date=date(2026, 10, 15),
        )

    valid = service.allocate(
        allocation_id="allocation:valid",
        settlement=_settlement("settlement:valid", "100.00"),
        subledger_item=receivable,
        due_item_id="due:a",
        amount=_money("100.00"),
        allocation_date=date(2026, 10, 15),
    )
    with pytest.raises(AllocationConcurrencyConflictError):
        service.allocate(
            allocation_id="allocation:stale",
            settlement=_settlement("settlement:other", "100.00"),
            subledger_item=valid.subledger_item,
            due_item_id="due:a",
            amount=_money("100.00"),
            allocation_date=date(2026, 10, 16),
            expected_due_item_revision=0,
        )


def test_settlement_reversal_restores_allocations_and_requires_posted_reversal() -> None:
    allocation_service = SettlementAllocationService()
    allocated = allocation_service.allocate(
        allocation_id="allocation:1",
        settlement=_settlement("settlement:1", "500.00"),
        subledger_item=_receivable(),
        due_item_id="due:a",
        amount=_money("500.00"),
        allocation_date=date(2026, 10, 15),
    )

    result = SettlementReversalService(allocation_service).reverse(
        reversal_id="settlement-reversal:1",
        settlement=allocated.settlement,
        subledger_items=(allocated.subledger_item,),
        allocations=(allocated.allocation,),
        reversed_at=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
        accounting_reversal_reference=_posted_reference("entry:settlement-reversal"),
        reason="bank settlement cancelled",
        expected_settlement_revision=1,
        expected_due_item_revisions={"due:a": 1},
    )

    assert result.settlement.status is SettlementStatus.REVERSED
    assert result.settlement.accounting_status is AccountingEffectStatus.REVERSED
    assert result.settlement.open_amount == _money("500.00")
    assert result.settlement.reversal_accounting_reference is not None
    assert result.subledger_items[0].open_amount == _money("1200.00")
    assert result.allocations[0].status is AllocationStatus.REVERSED


def test_payment_term_rounding_assigns_residue_to_final_rule() -> None:
    term = PaymentTerm(
        payment_term_id="term:thirds",
        code="THIRDS",
        version="1",
        rules=(
            DueDateRule("a", 30, Decimal("0.3333"), 1),
            DueDateRule("b", 60, Decimal("0.3333"), 2),
            DueDateRule("c", 90, Decimal("0.3334"), 3),
        ),
    )
    due_items = term.generate_due_items(
        entity_id=ENTITY,
        source_subledger_item_id="rec:term",
        document_date=date(2026, 9, 1),
        amount=_money("100.00"),
    )

    assert tuple(item.original_amount for item in due_items) == (
        _money("33.33"),
        _money("33.33"),
        _money("33.34"),
    )
    assert sum((item.original_amount.amount for item in due_items), Decimal("0")) == Decimal(
        "100.00"
    )


def test_matching_candidate_requires_explicit_validation() -> None:
    candidate = MatchingCandidate(
        candidate_id="candidate:1",
        entity_id=ENTITY,
        subledger_id=AR,
        party_id=PARTY,
        items=(
            _match_item("invoice", MatchSide.DEBIT, "100.00"),
            _match_item("credit-note", MatchSide.CREDIT, "80.00"),
        ),
    )
    with pytest.raises(NonExecutableMatchingError):
        candidate.assert_executable()
    with pytest.raises(NonExecutableMatchingError):
        candidate.validate(
            match_id="match:1",
            validated_at=datetime(2026, 10, 15, tzinfo=UTC),
        )

    validated = candidate.validate(
        match_id="match:1",
        validated_at=datetime(2026, 10, 15, tzinfo=UTC),
        residual_amount=_money("20.00"),
    )
    validated.assert_executable()
    assert validated.matched_amount == _money("80.00")
    assert validated.residual_amount == _money("20.00")
    assert validated.residual_side is MatchSide.DEBIT


def test_aging_snapshot_partitions_every_open_source_once() -> None:
    allocation = SettlementAllocationService().allocate(
        allocation_id="allocation:aging",
        settlement=_settlement("settlement:aging", "500.00"),
        subledger_item=_receivable(),
        due_item_id="due:a",
        amount=_money("500.00"),
        allocation_date=date(2026, 10, 15),
    )
    receivable = allocation.subledger_item
    sources = tuple(AgingSourceItem.from_receivable(receivable, due) for due in receivable.due_items)

    snapshot = AgingEngine().snapshot(
        entity_id=ENTITY,
        subledger_id=AR,
        as_of=date(2026, 12, 31),
        currency=EUR,
        policy=_aging_policy(),
        sources=sources,
    )

    assert snapshot.total_open == _money("700.00")
    totals = {bucket.bucket_id: bucket.total for bucket in snapshot.buckets}
    assert totals["31_60"] == _money("600.00")
    assert totals["61_PLUS"] == _money("100.00")
    assert len(snapshot.source_ids) == 2


def test_reconciliation_compares_open_items_with_normalized_gl_balance() -> None:
    allocation = SettlementAllocationService().allocate(
        allocation_id="allocation:recon",
        settlement=_settlement("settlement:recon", "500.00"),
        subledger_item=_receivable(),
        due_item_id="due:a",
        amount=_money("500.00"),
        allocation_date=date(2026, 10, 15),
    )
    receivable = allocation.subledger_item
    open_items = tuple(
        OpenItem.from_receivable(
            open_item_id=f"open:{due.due_item_id}",
            receivable=receivable,
            due_item=due,
        )
        for due in receivable.due_items
        if not due.open_amount.is_zero()
    )
    control = ResolvedControlAccount(
        binding_id="binding:ar",
        account_id=AccountId("account:411"),
        account_code="411000",
        entity_id=ENTITY,
        subledger_id=AR,
        chart_id="chart:pcg",
        chart_version="2026",
        reference_snapshot_id="snapshot:pcg:2026",
    )

    matched = SubledgerReconciliationService().reconcile(
        entity_id=ENTITY,
        subledger_id=AR,
        as_of=date(2026, 12, 31),
        currency=EUR,
        control_account=control,
        open_items=open_items,
        normalized_gl_balance=_money("700.00"),
    )
    difference = SubledgerReconciliationService().reconcile(
        entity_id=ENTITY,
        subledger_id=AR,
        as_of=date(2026, 12, 31),
        currency=EUR,
        control_account=control,
        open_items=open_items,
        normalized_gl_balance=_money("699.00"),
    )

    assert matched.status is SubledgerReconciliationStatus.MATCHED
    assert matched.difference.is_zero()
    assert difference.status is SubledgerReconciliationStatus.DIFFERENCE
    assert difference.difference == _money("1.00")


def test_write_off_request_requires_policy_and_proposal_evidence() -> None:
    with pytest.raises(WriteOffPolicyRequiredError):
        WriteOffRequest.create(
            request_id="write-off:1",
            entity_id=ENTITY,
            subledger_id=AR,
            source_item_id="rec:1",
            due_item_id="due:a",
            amount=_money("10.00"),
            authorization=None,
        )

    request = WriteOffRequest.create(
        request_id="write-off:1",
        entity_id=ENTITY,
        subledger_id=AR,
        source_item_id="rec:1",
        due_item_id="due:a",
        amount=_money("10.00"),
        authorization=WriteOffAuthorization(
            policy_set_id="policy-set:write-off",
            policy_version="1",
            proposal_checksum="abc123",
        ),
    )
    assert request.amount == _money("10.00")


def test_settlement_accounting_reference_is_entity_scoped() -> None:
    settlement = Settlement.create(
        settlement_id="settlement:entity",
        entity_id=ENTITY,
        subledger_id=AR,
        settlement_date=date(2026, 10, 15),
        accounting_date=date(2026, 10, 15),
        amount=_money("100.00"),
        source_reference="bank:entity",
    )
    with pytest.raises(Exception):
        settlement.link_posted_accounting(
            _posted_reference("entry:other", entity_id=OTHER_ENTITY)
        )
