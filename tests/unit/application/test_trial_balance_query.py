"""Unit tests for the TrialBalanceQuery use-case (LOT-07)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.application.reporting.trial_balance_query import TrialBalanceQuery
from pyaccountingkit.core.currency import EUR
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
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.reporting.trial_balance import TrialBalanceSnapshot

PERIOD = "p_2024_01"


def _posted(entry_id: str, debit_code: str, amount: str) -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JournalId("j"),
        period_id=PeriodId(PERIOD),
        entry_date=date(2024, 1, 10),
        description="posted",
        status=EntryStatus.POSTED,
        posted_at=datetime(2024, 1, 10, 8, 0, tzinfo=UTC),
        lines=(
            JournalLine(
                account_id=debit_code,
                debit=Money.from_str(amount, EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id="707000",
                debit=Money.zero(EUR),
                credit=Money.from_str(amount, EUR),
            ),
        ),
    )


def _chart() -> CompanyChartOfAccounts:
    return CompanyChartOfAccounts(
        entity_id=EntityId("ent"),
        accounts=(
            CompanyAccount(
                id=AccountId("411000"),
                entity_id=EntityId("ent"),
                code="411000",
                label="Clients",
            ),
            CompanyAccount(
                id=AccountId("707000"),
                entity_id=EntityId("ent"),
                code="707000",
                label="Ventes",
            ),
        ),
    )


def _app() -> tuple[TrialBalanceQuery, InMemoryUnitOfWorkFactory, InMemoryStore]:
    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)
    with factory.open() as uow:
        uow.periods.add(
            AccountingPeriod(
                id=PeriodId(PERIOD),
                entity_id=EntityId("ent"),
                fiscal_year_id=FiscalYearId("fy"),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )
        )
        uow.journals.add(
            Journal(id=JournalId("j"), entity_id=EntityId("ent"), code="V", label="Ventes")
        )
        uow.commit()
    query = TrialBalanceQuery(factory, _chart())
    return query, factory, store


def test_balance_aggregates_posted_entries() -> None:
    query, factory, store = _app()
    with factory.open() as uow:
        uow.entries.add(_posted("e1", "411000", "250.50"))
        uow.entries.add(_posted("e2", "411000", "10.00"))
        uow.commit()
    tb = query.balance_for(PERIOD)
    assert tb.total_debit == Money.from_str("260.50", EUR)
    assert tb.total_credit == Money.from_str("260.50", EUR)
    clients = tb.lines_for_account("411000")
    assert clients.sum_debit == Money.from_str("260.50", EUR)
    assert clients.label == "Clients"


def test_draft_entries_are_excluded() -> None:
    query, factory, store = _app()
    with factory.open() as uow:
        uow.entries.add(_posted("e1", "411000", "100.00"))
        draft = _posted("e_draft", "411000", "999.00")
        draft = JournalEntry(
            id=draft.id,
            journal_id=draft.journal_id,
            period_id=draft.period_id,
            entry_date=draft.entry_date,
            description=draft.description,
            lines=draft.lines,
            status=EntryStatus.DRAFT,
        )
        uow.entries.add(draft)
        uow.commit()
    tb = query.balance_for(PERIOD)
    assert tb.lines_for_account("411000").sum_debit == Money.from_str("100.00", EUR)


def test_empty_period_produces_empty_trial_balance() -> None:
    query, _, _ = _app()
    tb = query.balance_for(PERIOD)
    assert tb.lines == ()
    assert tb.total_debit == Money.zero(EUR)
    assert tb.total_credit == Money.zero(EUR)


def test_snapshot_label_respected() -> None:
    query, _, _ = _app()
    tb = query.balance_for(PERIOD, TrialBalanceSnapshot.ADJUSTED)
    assert tb.snapshot is TrialBalanceSnapshot.ADJUSTED


def test_deterministic_positions_across_calls() -> None:
    query, factory, store = _app()
    with factory.open() as uow:
        uow.entries.add(_posted("e1", "411000", "50.00"))
        uow.commit()
    assert [line.account_code for line in query.balance_for(PERIOD).lines] == [
        "411000",
        "707000",
    ]
    assert [line.account_code for line in query.balance_for(PERIOD).lines] == [
        "411000",
        "707000",
    ]


def test_drill_down_to_entry_lines() -> None:
    query, factory, store = _app()
    with factory.open() as uow:
        uow.entries.add(_posted("e1", "411000", "50.00"))
        uow.commit()
    drilled = query.drill_down(PERIOD, "411000")
    assert len(drilled) == 1
    entry_id, line = drilled[0]
    assert entry_id == EntryId("e1")
    assert line.debit == Money.from_str("50.00", EUR)


def test_drill_down_empty_for_unknown_account() -> None:
    query, factory, store = _app()
    with factory.open() as uow:
        uow.entries.add(_posted("e1", "411000", "50.00"))
        uow.commit()
    assert query.drill_down(PERIOD, "999999") == ()
