"""Reference-specific behaviors of the in-memory adapter."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.in_memory.unit_of_work import (
    InMemoryUnitOfWork,
    InMemoryUnitOfWorkFactory,
)
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import RevisionConflictError
from pyaccountingkit.core.identifiers import EntityId, EntryId, FiscalYearId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.ports.outbox import OutboxRecord


def _entry(entry_id: str = "e1") -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JournalId("j"),
        period_id=PeriodId("p"),
        entry_date=date(2024, 1, 1),
        description="test",
        lines=(
            JournalLine(
                account_id="411000",
                debit=Money.from_str("10.00", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id="707000",
                debit=Money.zero(EUR),
                credit=Money.from_str("10.00", EUR),
            ),
        ),
    )


def test_rollback_leaves_no_partial_state() -> None:
    factory = InMemoryUnitOfWorkFactory()
    with factory.open() as uow:
        uow.entries.add(_entry("e1"))
        uow.entries.add(_entry("e2"))
        uow.periods.add(
            AccountingPeriod(
                id=PeriodId("p"),
                entity_id=EntityId("ent"),
                fiscal_year_id=FiscalYearId("fy"),
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )
        )
        uow.rollback()
    store = factory.store
    assert store.entries == {}
    assert store.periods == {}


def test_concurrent_commit_bumps_revision() -> None:
    factory = InMemoryUnitOfWorkFactory()
    with factory.open() as uow:
        uow.entries.add(_entry())
        uow.commit()
    with factory.open() as uow:
        entry = uow.entries.get(EntryId("e1"))
        uow.entries.save(entry, uow.entries.get_revision(EntryId("e1")))
        uow.commit()
    assert factory.store.entry_revisions[EntryId("e1")].value == 1


def test_duplicate_period_and_journal_rejected() -> None:
    store = InMemoryStore()
    with InMemoryUnitOfWork(store) as uow:
        period = AccountingPeriod(
            id=PeriodId("p"),
            entity_id=EntityId("ent"),
            fiscal_year_id=FiscalYearId("fy"),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        journal = Journal(id=JournalId("j"), entity_id=EntityId("ent"), code="J", label="Journal")
        uow.periods.add(period)
        uow.journals.add(journal)
        uow.commit()
    store_before = store.copy()
    with InMemoryUnitOfWork(store) as uow:
        with pytest.raises(RevisionConflictError):
            uow.periods.add(period)
        uow.rollback()
    assert store.periods == store_before.periods
    with InMemoryUnitOfWork(store) as uow:
        with pytest.raises(RevisionConflictError):
            uow.journals.add(journal)
        uow.rollback()
    assert store.journals == store_before.journals


def test_audit_records_discarded_by_rollback() -> None:
    factory = InMemoryUnitOfWorkFactory()
    event = AuditEvent(
        event_type="ENTRY_POSTED",
        entity_id="e1",
        actor_id="user:1",
        occurred_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    with factory.open() as uow:
        uow.audit.record(event)
        uow.rollback()
    assert factory.store.audit_log == []
    with factory.open() as uow:
        uow.audit.record(event)
        uow.commit()
    assert factory.store.audit_log == [event]


def test_outbox_drain_after_commit() -> None:
    factory = InMemoryUnitOfWorkFactory()
    record = OutboxRecord(event_type="ENTRY_QUEUED", entity_id="e1")
    with factory.open() as uow:
        uow.outbox.publish(record)
        uow.commit()
    drained = factory.store.drain_outbox()
    assert drained == [record]
    assert factory.store.drain_outbox() == []


def test_clock_is_injectable_into_uow() -> None:
    frozen = FrozenClock(datetime(2026, 1, 1, tzinfo=UTC))
    store = InMemoryStore()
    with InMemoryUnitOfWork(store, clock=frozen) as uow:
        assert uow.clock.now() == datetime(2026, 1, 1, tzinfo=UTC)


def test_commit_outside_context_raises() -> None:
    uow = InMemoryUnitOfWork(InMemoryStore())
    with pytest.raises(RuntimeError, match="un-entered"):
        uow.commit()
