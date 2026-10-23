"""LOT-34R qualification for the persistent subledger application chain."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.adapters.in_memory.company_chart_resolver import (
    InMemoryVersionedCompanyChartResolver,
)
from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.application.ledger.reversal_orchestrator import ReversalOrchestrator
from pyaccountingkit.application.subledgers import PersistentSubledgerApplicationService
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import RevisionConflictError
from pyaccountingkit.core.identifiers import (
    AccountId,
    EntityId,
    EntryId,
    FiscalYearId,
    JournalId,
    PeriodId,
)
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.charts.company_chart import (
    ChartStatus,
    CompanyChart,
    CompanyChartVersion,
)
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.subledgers.allocation import AllocationStatus
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.errors import AllocationConcurrencyConflictError
from pyaccountingkit.domain.subledgers.parties import SubledgerParty
from pyaccountingkit.domain.subledgers.primitives import (
    AccountingEffectStatus,
    OperationalItemStatus,
    SubledgerPartyType,
)
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.settlement import Settlement, SettlementStatus

NOW = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)
ENTITY = EntityId("entity:subledger")
PERIOD_ID = PeriodId("period:2026-10")
JOURNAL_ID = JournalId("journal:sales")
AR = "subledger:ar"
PARTY_ID = "party:customer"


def _money(value: str) -> Money:
    return Money.from_str(value, EUR)


def _chart_resolver() -> InMemoryVersionedCompanyChartResolver:
    chart = CompanyChartOfAccounts(
        entity_id=ENTITY,
        accounts=(
            CompanyAccount(
                id=AccountId("411000"),
                entity_id=ENTITY,
                code="411000",
                label="Customers",
            ),
            CompanyAccount(
                id=AccountId("707000"),
                entity_id=ENTITY,
                code="707000",
                label="Revenue",
            ),
            CompanyAccount(
                id=AccountId("512000"),
                entity_id=ENTITY,
                code="512000",
                label="Bank",
            ),
        ),
    )
    config = CompanyChart(
        chart_id="chart:subledger",
        entity_id=ENTITY,
        code="STD",
        label="Standard",
        primary_standard="fr-pcg",
        code_policy_id="numeric",
        reference_snapshot_id="snapshot:1",
        versions=(
            CompanyChartVersion(
                label="v1",
                status=ChartStatus.ACTIVE,
                effective_from=date(2026, 1, 1),
            ),
        ),
    )
    return InMemoryVersionedCompanyChartResolver(config, {"v1": chart})


def _runtime() -> tuple[
    PersistentSubledgerApplicationService,
    InMemoryUnitOfWorkFactory,
    InMemoryStore,
]:
    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)
    with factory.open() as uow:
        uow.periods.add(
            AccountingPeriod(
                id=PERIOD_ID,
                entity_id=ENTITY,
                fiscal_year_id=FiscalYearId("fy:2026"),
                start_date=date(2026, 10, 1),
                end_date=date(2026, 10, 31),
            )
        )
        uow.journals.add(
            Journal(
                id=JOURNAL_ID,
                entity_id=ENTITY,
                code="SAL",
                label="Sales",
            )
        )
        uow.commit()

    posting = PostingOrchestrator(
        factory,
        _chart_resolver(),
        PostingService(clock=FrozenClock(NOW)),
    )
    reversal_ids = iter(("entry:reversal:1", "entry:reversal:2"))
    reversal = ReversalOrchestrator(
        factory,
        lambda: EntryId(next(reversal_ids)),
    )
    service = PersistentSubledgerApplicationService(factory, posting, reversal)
    service.partners.create(
        party=SubledgerParty(
            party_id=PARTY_ID,
            entity_id=ENTITY,
            party_type=SubledgerPartyType.CUSTOMER,
            display_name="Customer",
        )
    )
    return service, factory, store


def _entry(
    entry_id: str,
    *,
    debit_account: str,
    credit_account: str,
    amount: str,
) -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JOURNAL_ID,
        period_id=PERIOD_ID,
        entry_date=date(2026, 10, 23),
        description=entry_id,
        lines=(
            JournalLine(
                account_id=AccountId(debit_account),
                debit=_money(amount),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id=AccountId(credit_account),
                debit=Money.zero(EUR),
                credit=_money(amount),
            ),
        ),
    ).validate()


def _receivable(identifier: str = "receivable:1") -> Receivable:
    amount = _money("100.00")
    return Receivable(
        receivable_id=identifier,
        entity_id=ENTITY,
        subledger_id=AR,
        party_id=PARTY_ID,
        source_document_ref=f"invoice:{identifier}",
        original_amount=amount,
        accounting_date=date(2026, 10, 23),
        due_items=(
            DueItem.create(
                due_item_id=f"due:{identifier}",
                entity_id=ENTITY,
                source_subledger_item_id=identifier,
                due_date=date(2026, 11, 23),
                original_amount=amount,
            ),
        ),
    )


def _recognize(
    service: PersistentSubledgerApplicationService,
    identifier: str = "receivable:1",
    entry_id: str = "entry:invoice:1",
) -> Receivable:
    return service.receivables.recognize(
        receivable=_receivable(identifier),
        entry=_entry(
            entry_id,
            debit_account="411000",
            credit_account="707000",
            amount="100.00",
        ),
        actor_id="user:test",
    )


def _record_settlement(
    service: PersistentSubledgerApplicationService,
) -> Settlement:
    return service.settlements.record(
        settlement=Settlement.create(
            settlement_id="settlement:1",
            entity_id=ENTITY,
            subledger_id=AR,
            settlement_date=date(2026, 10, 23),
            accounting_date=date(2026, 10, 23),
            amount=_money("60.00"),
            source_reference="payment:1",
            party_id=PARTY_ID,
        ),
        entry=_entry(
            "entry:payment:1",
            debit_account="512000",
            credit_account="411000",
            amount="60.00",
        ),
        actor_id="user:test",
    )


def test_recognize_receivable_posts_gl_and_persists_atomically() -> None:
    service, factory, store = _runtime()

    recognized = _recognize(service)

    assert recognized.operational_status is OperationalItemStatus.OPEN
    assert recognized.accounting_status is AccountingEffectStatus.POSTED
    assert recognized.accounting_reference is not None
    assert recognized.accounting_reference.entry_id == EntryId("entry:invoice:1")
    assert store.entries[EntryId("entry:invoice:1")].status is EntryStatus.POSTED
    with factory.open() as uow:
        assert uow.subledgers.get_receivable("receivable:1") == recognized


def test_failed_subledger_write_rolls_back_gl_posting() -> None:
    service, factory, store = _runtime()
    duplicate = _receivable("receivable:duplicate")
    with factory.open() as uow:
        uow.subledgers.add_receivable(duplicate)
        uow.commit()

    with pytest.raises(RevisionConflictError):
        service.receivables.recognize(
            receivable=duplicate,
            entry=_entry(
                "entry:rollback",
                debit_account="411000",
                credit_account="707000",
                amount="100.00",
            ),
            actor_id="user:test",
        )

    assert EntryId("entry:rollback") not in store.entries
    assert "post:entry:rollback" not in store.idempotency
    assert all(record.payload.get("entry_id") != "entry:rollback" for record in store.outbox)


def test_allocation_persists_item_settlement_and_evidence_atomically() -> None:
    service, factory, _ = _runtime()
    receivable = _recognize(service)
    settlement = _record_settlement(service)

    result = service.settlements.allocate(
        allocation_id="allocation:1",
        settlement_id=settlement.settlement_id,
        source_item_id=receivable.receivable_id,
        due_item_id=receivable.due_items[0].due_item_id,
        amount=_money("40.00"),
        allocation_date=date(2026, 10, 23),
        expected_settlement_revision=0,
        expected_due_item_revision=0,
    )

    assert result.settlement.open_amount == _money("20.00")
    assert result.subledger_item.open_amount == _money("60.00")
    assert result.allocation.status is AllocationStatus.ACTIVE

    with factory.open() as uow:
        persisted_settlement = uow.subledgers.get_settlement("settlement:1")
        persisted_receivable = uow.subledgers.get_receivable("receivable:1")
        allocations = uow.subledgers.list_allocations("settlement:1")

    assert persisted_settlement == result.settlement
    assert persisted_receivable == result.subledger_item
    assert allocations == (result.allocation,)


def test_stale_allocation_fails_without_partial_state() -> None:
    service, factory, _ = _runtime()
    receivable = _recognize(service)
    settlement = _record_settlement(service)
    first = service.settlements.allocate(
        allocation_id="allocation:1",
        settlement_id=settlement.settlement_id,
        source_item_id=receivable.receivable_id,
        due_item_id=receivable.due_items[0].due_item_id,
        amount=_money("40.00"),
        allocation_date=date(2026, 10, 23),
        expected_settlement_revision=0,
        expected_due_item_revision=0,
    )

    with pytest.raises(AllocationConcurrencyConflictError):
        service.settlements.allocate(
            allocation_id="allocation:stale",
            settlement_id=settlement.settlement_id,
            source_item_id=receivable.receivable_id,
            due_item_id=receivable.due_items[0].due_item_id,
            amount=_money("10.00"),
            allocation_date=date(2026, 10, 23),
            expected_settlement_revision=0,
            expected_due_item_revision=0,
        )

    with factory.open() as uow:
        assert uow.subledgers.get_settlement("settlement:1") == first.settlement
        assert uow.subledgers.get_receivable("receivable:1") == first.subledger_item
        assert uow.subledgers.list_allocations("settlement:1") == (first.allocation,)


def test_settlement_reversal_restores_due_item_and_gl_in_one_transaction() -> None:
    service, factory, store = _runtime()
    receivable = _recognize(service)
    settlement = _record_settlement(service)
    allocated = service.settlements.allocate(
        allocation_id="allocation:1",
        settlement_id=settlement.settlement_id,
        source_item_id=receivable.receivable_id,
        due_item_id=receivable.due_items[0].due_item_id,
        amount=_money("40.00"),
        allocation_date=date(2026, 10, 23),
        expected_settlement_revision=0,
        expected_due_item_revision=0,
    )

    reversed_result = service.settlements.reverse(
        settlement_id="settlement:1",
        target_period_id=PERIOD_ID,
        reversal_date=date(2026, 10, 23),
        actor_id="user:test",
        reversal_id="settlement-reversal:1",
        reason="Payment cancelled",
        reversed_at=NOW,
        expected_settlement_revision=allocated.settlement.revision,
        expected_due_item_revisions={
            allocated.subledger_item.due_items[0].due_item_id: allocated.subledger_item.due_items[
                0
            ].revision
        },
    )

    assert reversed_result.settlement.status is SettlementStatus.REVERSED
    assert reversed_result.settlement.open_amount == _money("60.00")
    assert reversed_result.subledger_items[0].open_amount == _money("100.00")
    assert reversed_result.allocations[0].status is AllocationStatus.REVERSED

    original_payment = store.entries[EntryId("entry:payment:1")]
    assert original_payment.status is EntryStatus.REVERSED
    assert original_payment.reversed_by_id == EntryId("entry:reversal:1")
    assert store.entries[EntryId("entry:reversal:1")].status is EntryStatus.POSTED

    with factory.open() as uow:
        assert uow.subledgers.get_settlement("settlement:1") == reversed_result.settlement
        assert uow.subledgers.get_reversal("settlement-reversal:1") == reversed_result.reversal
