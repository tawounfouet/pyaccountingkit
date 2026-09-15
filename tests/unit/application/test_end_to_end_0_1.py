"""End-to-end 0.1 core scenario — the release's required scenario (ROADMAP)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.application.closing.closing_orchestrator import ClosingOrchestrator
from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.application.ledger.reversal_orchestrator import ReversalOrchestrator
from pyaccountingkit.application.reporting.ledger_queries import GeneralLedgerQuery, JournalQuery
from pyaccountingkit.application.reporting.trial_balance_query import TrialBalanceQuery
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import PeriodClosedError
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
from pyaccountingkit.domain.closing.closing_run import CloseGate, ClosingRunBook
from pyaccountingkit.domain.controls.control import ControlOutcome, ControlResult, ControlRun
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus
from pyaccountingkit.domain.reporting.trial_balance import TrialBalanceSnapshot

NOW = datetime(2024, 12, 31, 18, 0, tzinfo=UTC)


def _chart(entity: EntityId) -> CompanyChartOfAccounts:
    accounts = (
        CompanyAccount(
            id=AccountId("411000"),
            entity_id=entity,
            code="411000",
            label="Clients",
        ),
        CompanyAccount(
            id=AccountId("707000"),
            entity_id=entity,
            code="707000",
            label="Ventes",
        ),
    )
    return CompanyChartOfAccounts(entity_id=entity, accounts=accounts)


def test_0_1_core_scenario_end_to_end() -> None:
    entity = EntityId("ent")
    fy = FiscalYearId("fy")
    period = PeriodId("p_2024_12")
    next_period = PeriodId("p_2025_01")
    journal_id = JournalId("j_ventes")

    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)

    with factory.open() as uow:
        uow.periods.add(
            AccountingPeriod(
                id=period,
                entity_id=entity,
                fiscal_year_id=fy,
                start_date=date(2024, 12, 1),
                end_date=date(2024, 12, 31),
                status=ClosingStatus.OPEN,
            )
        )
        uow.journals.add(Journal(id=journal_id, entity_id=entity, code="V", label="Ventes"))
        uow.commit()

    chart = _chart(entity)
    clock = FrozenClock(NOW)
    svc = PostingService(clock=clock)
    posting = PostingOrchestrator(factory, chart, svc)
    reversal = ReversalOrchestrator(factory, lambda: EntryId("rev1"))
    tb_query = TrialBalanceQuery(factory, chart)
    journal_query = JournalQuery(factory)
    ledger_query = GeneralLedgerQuery(factory)

    entry = _draft("e1")

    result = posting.post(entry, actor_id="u1")
    assert result.posted_entry.status is EntryStatus.POSTED
    assert store.audit_log[-1].event_type == "ENTRY_POSTED"
    assert len(journal_query.entries_for(journal_id, period)) == 1
    assert len(ledger_query.account_ledger(period, "411000")) == 1

    tb = tb_query.balance_for(period, TrialBalanceSnapshot.BEFORE_ADJUSTMENTS)
    assert tb.total_debit == tb.total_credit
    assert tb.lines_for_account("411000").balance == money("250.50")

    reverted = reversal.reverse(
        entry_id=EntryId("e1"),
        target_period_id=period,
        reversal_date=date(2024, 12, 31),
        actor_id="u1",
    )
    assert reverted.reversal_entry.reversal_of_id == EntryId("e1")
    assert store.entries[EntryId("e1")].reversed_by_id == EntryId("rev1")

    tb_after = tb_query.balance_for(period, TrialBalanceSnapshot.ADJUSTED)
    assert tb_after.lines_for_account("411000").is_zero

    post_closing = tb_query.balance_for(period, TrialBalanceSnapshot.POST_CLOSING)
    assert post_closing.lines_for_account("411000").is_zero

    controls = (
        ControlRun(
            id="cr_balance",
            definition_code="BALANCE",
            version=1,
            period_id=str(period),
            result=ControlResult(outcome=ControlOutcome.PASS, detail="ok"),
            executed_at=NOW,
        ),
    )
    gate = CloseGate()
    gate.require("BALANCE")
    closing = ClosingOrchestrator(
        factory,
        ClosingRunBook(),
        gate,
        run_id_factory=lambda: "c1",
        clock=clock,
    )
    closing.close_period(
        period,
        control_runs=controls,
        trial_balance=post_closing,
        next_period_id=next_period,
        opening_journal_id=journal_id,
        opening_entry_id=EntryId("o2025"),
        opening_date=date(2025, 1, 1),
    )
    assert store.periods[period].status is ClosingStatus.CLOSED

    with pytest.raises(PeriodClosedError):
        posting.post(_draft("e2"), actor_id="u1")

    assert EntryId("o2025") not in store.entries


def _draft(entry_id: str, description: str = "Vente du 15/12") -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JournalId("j_ventes"),
        period_id=PeriodId("p_2024_12"),
        entry_date=date(2024, 12, 15),
        description=description,
        lines=(
            JournalLine(
                account_id=AccountId("411000"),
                debit=Money.from_str("250.50", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id=AccountId("707000"),
                debit=Money.zero(EUR),
                credit=Money.from_str("250.50", EUR),
            ),
        ),
    )


def money(value: str) -> Money:
    return Money.from_str(value, EUR)
