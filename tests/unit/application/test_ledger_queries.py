"""Unit tests for JournalQuery and GeneralLedgerQuery (LOT-07)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.application.reporting.ledger_queries import (
    GeneralLedgerQuery,
    JournalQuery,
)
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine


def _posted(
    entry_id: str,
    account: str,
    amount: str,
    day: int,
) -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JournalId("j_ventes"),
        period_id=PeriodId("p_2024_01"),
        entry_date=date(2024, 1, day),
        description="vente",
        status=EntryStatus.POSTED,
        posted_at=datetime(2024, 1, day, 8, 0, tzinfo=UTC),
        lines=(
            JournalLine(
                account_id=account,
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


def _app() -> tuple[InMemoryUnitOfWorkFactory, InMemoryStore]:
    store = InMemoryStore()
    factory = InMemoryUnitOfWorkFactory(store)
    return factory, store


def test_journal_query_returns_only_posted_in_order() -> None:
    factory, store = _app()
    with factory.open() as uow:
        uow.entries.add(_posted("e2", "411000", "20.00", day=20))
        uow.entries.add(_posted("e1", "411000", "10.00", day=10))
        uow.commit()
    query = JournalQuery(factory)
    entries = query.entries_for(JournalId("j_ventes"))
    assert [e.id for e in entries] == [EntryId("e1"), EntryId("e2")]


def test_journal_query_filters_by_period() -> None:
    factory, store = _app()
    with factory.open() as uow:
        uow.entries.add(_posted("e1", "411000", "10.00", day=10))
        other = _posted("e_other", "411000", "5.00", day=5)
        other = JournalEntry(
            id=other.id,
            journal_id=other.journal_id,
            period_id=PeriodId("p_other"),
            entry_date=other.entry_date,
            description=other.description,
            lines=other.lines,
            status=EntryStatus.POSTED,
            posted_at=other.posted_at,
        )
        uow.entries.add(other)
        uow.commit()
    query = JournalQuery(factory)
    entries = query.entries_for(JournalId("j_ventes"), period_id=PeriodId("p_2024_01"))
    assert [e.id for e in entries] == [EntryId("e1")]


def test_general_ledger_running_balance() -> None:
    factory, store = _app()
    with factory.open() as uow:
        uow.entries.add(_posted("e1", "411000", "100.00", day=10))
        uow.entries.add(_posted("e2", "411000", "50.00", day=20))
        uow.commit()
    query = GeneralLedgerQuery(factory)
    positions = query.account_ledger(PeriodId("p_2024_01"), "411000")
    assert [p.running_balance for p in positions] == [
        Money.from_str("100.00", EUR),
        Money.from_str("150.00", EUR),
    ]
    assert positions[0].entry_id == "e1"
    assert positions[1].entry_id == "e2"


def test_general_ledger_ignores_other_accounts() -> None:
    factory, store = _app()
    with factory.open() as uow:
        uow.entries.add(_posted("e1", "411000", "100.00", day=10))
        uow.commit()
    query = GeneralLedgerQuery(factory)
    missing = query.account_ledger(PeriodId("p_2024_01"), "999999")
    assert missing == ()
