"""Reusable repository/UnitOfWork contract tests.

These tests are written against the ports only and are reused by every
persistence adapter (in-memory reference today, SQLAlchemy/PostgreSQL and
Django adapters later).  Add a new factory to FACTORIES to extend coverage.
"""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import (
    EntryNotFoundError,
    RevisionConflictError,
)
from pyaccountingkit.core.identifiers import EntityId, EntryId, FiscalYearId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.core.revisions import Revision
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.ports.outbox import OutboxRecord
from pyaccountingkit.ports.unit_of_work import UnitOfWorkFactoryProtocol

FACTORIES: list[str] = ["in_memory"]


def _new_factory(name: str) -> UnitOfWorkFactoryProtocol:
    if name == "in_memory":
        return InMemoryUnitOfWorkFactory()
    raise AssertionError(f"Unknown repository factory: {name}")


def _balanced_entry(entry_id: EntryId | None = None) -> JournalEntry:
    return JournalEntry(
        id=entry_id or EntryId("entry_1"),
        journal_id=JournalId("j_ventes"),
        period_id=PeriodId("p_2024_01"),
        entry_date=date(2024, 1, 15),
        description="Vente TC",
        lines=(
            JournalLine(
                account_id="411000",
                debit=Money.from_str("100.00", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id="707000",
                debit=Money.zero(EUR),
                credit=Money.from_str("100.00", EUR),
            ),
        ),
    )


def _monthly_period() -> AccountingPeriod:
    return AccountingPeriod(
        id=PeriodId("p_2024_01"),
        entity_id=EntityId("ent_1"),
        fiscal_year_id=FiscalYearId("fy_2024"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )


def _sales_journal() -> Journal:
    return Journal(
        id=JournalId("j_ventes"),
        entity_id=EntityId("ent_1"),
        code="VENTES",
        label="Ventes",
    )


@pytest.fixture
def uow_factory() -> UnitOfWorkFactoryProtocol:
    return _new_factory("in_memory")


@pytest.mark.parametrize("name", FACTORIES)
def test_entry_add_and_get_roundtrip(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        entry = _balanced_entry()
        uow.entries.add(entry)
        assert uow.entries.get(entry.id) == entry
        uow.commit()


@pytest.mark.parametrize("name", FACTORIES)
def test_entry_add_twice_is_rejected(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        uow.entries.add(_balanced_entry())
        uow.commit()
    with factory.open() as uow:
        with pytest.raises(RevisionConflictError):
            uow.entries.add(_balanced_entry())
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_entry_get_missing_raises(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        with pytest.raises(EntryNotFoundError):
            uow.entries.get(EntryId("missing"))
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_save_with_stale_revision_conflicts(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        uow.entries.add(_balanced_entry())
        uow.commit()
    with factory.open() as uow:
        entry = uow.entries.get(EntryId("entry_1"))
        uow.entries.save(entry, Revision())
        uow.commit()
    with factory.open() as uow:
        posted = uow.entries.get(EntryId("entry_1"))
        with pytest.raises(RevisionConflictError):
            uow.entries.save(posted, Revision())
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_commit_persists_period_and_journal(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        period = _monthly_period()
        journal = _sales_journal()
        uow.periods.add(period)
        uow.journals.add(journal)
        uow.commit()
    with factory.open() as uow:
        assert uow.periods.get(period.id) == period
        assert uow.journals.get(journal.id) == journal
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_uncommitted_transaction_is_discarded(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        uow.entries.add(_balanced_entry())
    with factory.open() as uow:
        with pytest.raises(EntryNotFoundError):
            uow.entries.get(EntryId("entry_1"))
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_idempotency_key_claimed_once(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        assert uow.idempotency.claim("post:entry_1")
        uow.idempotency.complete("post:entry_1")
        uow.commit()
    with factory.open() as uow:
        assert not uow.idempotency.claim("post:entry_1")
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_outbox_message_buffered_until_commit(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        uow.outbox.publish(OutboxRecord(event_type="ENTRY_QUEUED", entity_id="entry_1"))
        uow.commit()
