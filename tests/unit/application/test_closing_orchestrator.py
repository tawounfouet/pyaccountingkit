"""Unit tests for the closing orchestrator (LOT-09)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.application.closing.closing_orchestrator import ClosingOrchestrator
from pyaccountingkit.application.ledger.posting_orchestrator import PostingOrchestrator
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import ControlFailureError, PeriodClosedError
from pyaccountingkit.core.identifiers import (
    AccountId,
    EntityId,
    EntryId,
    FiscalYearId,
    JournalId,
    PeriodId,
)
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.domain.charts.account import CompanyAccount
from pyaccountingkit.domain.charts.chart import CompanyChartOfAccounts
from pyaccountingkit.domain.closing.closing_run import CloseGate, ClosingRunBook
from pyaccountingkit.domain.controls.control import (
    ControlOutcome,
    ControlResult,
    ControlRun,
)
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.reporting.trial_balance import TrialBalance, TrialBalanceSnapshot

NOW = datetime(2024, 12, 31, 23, 0, tzinfo=UTC)


class RecordingAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


def _chart() -> CompanyChartOfAccounts:
    entity = EntityId("ent")
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


def _periods() -> dict[PeriodId, AccountingPeriod]:
    entity = EntityId("ent")
    fy = FiscalYearId("fy")
    return {
        PeriodId("p_2024_12"): AccountingPeriod(
            id=PeriodId("p_2024_12"),
            entity_id=entity,
            fiscal_year_id=fy,
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
            status=ClosingStatus.OPEN,
        ),
        PeriodId("p_2025_01"): AccountingPeriod(
            id=PeriodId("p_2025_01"),
            entity_id=entity,
            fiscal_year_id=fy,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            status=ClosingStatus.OPEN,
        ),
    }


def _tb() -> TrialBalance:
    lines = (
        AccountBalanceLine(
            account_code="411000",
            label="Clients",
            sum_debit=Money.from_str("250.00", EUR),
            sum_credit=Money.zero(EUR),
        ),
        AccountBalanceLine(
            account_code="707000",
            label="Ventes",
            sum_debit=Money.zero(EUR),
            sum_credit=Money.from_str("250.00", EUR),
        ),
    )
    return TrialBalance.build("p_2024_12", TrialBalanceSnapshot.POST_CLOSING, lines)


def _control(outcome: ControlOutcome, code: str = "BALANCE") -> ControlRun:
    return ControlRun(
        id=f"cr_{code}_{outcome.value}",
        definition_code=code,
        version=1,
        period_id="p_2024_12",
        result=ControlResult(outcome=outcome, detail="ok"),
        executed_at=NOW,
    )


def _build() -> tuple[ClosingOrchestrator, InMemoryUnitOfWorkFactory, InMemoryStore]:
    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)
    with factory.open() as uow:
        for period in _periods().values():
            uow.periods.add(period)
        uow.journals.add(
            Journal(id=JournalId("j_ventes"), entity_id=EntityId("ent"), code="V", label="Ventes")
        )
        uow.commit()
    book = ClosingRunBook()
    gate = CloseGate()
    gate.require("BALANCE")
    orchestrator = ClosingOrchestrator(
        factory,
        book,
        gate,
        run_id_factory=lambda: "c1",
        clock=FrozenClock(NOW),
    )
    return orchestrator, factory, store


def test_close_seals_period_and_records_evidence() -> None:
    orchestrator, factory, store = _build()
    run = orchestrator.close_period(
        PeriodId("p_2024_12"),
        control_runs=[
            _control(ControlOutcome.PASS),
        ],
        trial_balance=_tb(),
    )
    assert run.is_sealed
    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.CLOSED
    assert run.evidence is not None
    assert run.evidence.trial_balance_checksum == _tb().checksum


def test_post_rejected_after_close() -> None:
    orchestrator, factory, store = _build()
    chart = _chart()
    sink = RecordingAuditSink()
    svc = PostingService(clock=FrozenClock(NOW), audit_sink=sink)
    posting = PostingOrchestrator(factory, chart, svc)
    first = posting.post(_balanced_draft("e1"), actor_id="u1")
    assert first.posted_entry.status is EntryStatus.POSTED
    orchestrator.close_period(
        PeriodId("p_2024_12"),
        control_runs=[_control(ControlOutcome.PASS)],
        trial_balance=_tb(),
    )
    with pytest.raises(PeriodClosedError):
        posting.post(_balanced_draft("e2"), actor_id="u1")
    assert EntryId("e2") not in store.entries


def _balanced_draft(entry_id: str) -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JournalId("j_ventes"),
        period_id=PeriodId("p_2024_12"),
        entry_date=date(2024, 12, 15),
        description="Vente du 15/12",
        lines=(
            JournalLine(
                account_id="411000",
                debit=Money.from_str("250.00", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id="707000",
                debit=Money.zero(EUR),
                credit=Money.from_str("250.00", EUR),
            ),
        ),
    )


def test_blocking_control_failure_prevents_close() -> None:
    orchestrator, factory, store = _build()
    with pytest.raises(ControlFailureError):
        orchestrator.close_period(
            PeriodId("p_2024_12"),
            control_runs=[_control(ControlOutcome.FAIL)],
            trial_balance=_tb(),
        )
    assert store.periods[PeriodId("p_2024_12")].status is ClosingStatus.OPEN
    assert store.entries == {}


def test_close_generates_traceable_opening_balances() -> None:
    orchestrator, factory, store = _build()
    orchestrator.close_period(
        PeriodId("p_2024_12"),
        control_runs=[_control(ControlOutcome.PASS)],
        trial_balance=_tb(),
        next_period_id=PeriodId("p_2025_01"),
        opening_journal_id=JournalId("j_ventes"),
        opening_entry_id=EntryId("o2025"),
        opening_date=date(2025, 1, 1),
    )
    opening = store.entries[EntryId("o2025")]
    assert opening.period_id == PeriodId("p_2025_01")
    assert opening.status is EntryStatus.POSTED
    assert opening.is_balanced()
    assert "c1" in opening.description
    assert store.periods[PeriodId("p_2025_01")].status is ClosingStatus.OPEN
