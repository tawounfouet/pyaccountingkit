"""Concurrency qualification for the in-memory behavioral reference adapter."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import RevisionConflictError
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine


def _entry(entry_id: str = "e1") -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JournalId("j"),
        period_id=PeriodId("p"),
        entry_date=date(2026, 1, 1),
        description="concurrency fixture",
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


def test_competing_uows_reject_stale_entry_revision() -> None:
    factory = InMemoryUnitOfWorkFactory()
    with factory.open() as seed:
        seed.entries.add(_entry())
        seed.commit()

    uow_a = factory.open()
    uow_b = factory.open()
    uow_a.__enter__()
    uow_b.__enter__()
    try:
        entry_a = uow_a.entries.get(EntryId("e1"))
        entry_b = uow_b.entries.get(EntryId("e1"))
        revision_a = uow_a.entries.get_revision(EntryId("e1"))
        revision_b = uow_b.entries.get_revision(EntryId("e1"))

        posted_a = entry_a.freeze(datetime(2026, 1, 2, 10, 0, tzinfo=UTC))
        posted_b = entry_b.freeze(datetime(2026, 1, 2, 11, 0, tzinfo=UTC))
        uow_a.entries.save(posted_a, revision_a)
        uow_b.entries.save(posted_b, revision_b)

        uow_a.commit()
        with pytest.raises(RevisionConflictError, match="changed after UnitOfWork snapshot"):
            uow_b.commit()
    finally:
        uow_a.__exit__(None, None, None)
        uow_b.__exit__(None, None, None)

    assert factory.store.entries[EntryId("e1")].posted_at == datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
    assert factory.store.entry_revisions[EntryId("e1")].value == 1


def test_rollback_of_stale_uow_does_not_erase_other_commit() -> None:
    factory = InMemoryUnitOfWorkFactory()
    uow_a = factory.open()
    uow_b = factory.open()
    uow_a.__enter__()
    uow_b.__enter__()
    try:
        uow_a.entries.add(_entry("committed"))
        uow_b.entries.add(_entry("rolled_back"))
        uow_a.commit()
        uow_b.rollback()
    finally:
        uow_a.__exit__(None, None, None)
        uow_b.__exit__(None, None, None)

    assert EntryId("committed") in factory.store.entries
    assert EntryId("rolled_back") not in factory.store.entries


def test_competing_idempotency_claims_conflict_at_commit() -> None:
    factory = InMemoryUnitOfWorkFactory()
    uow_a = factory.open()
    uow_b = factory.open()
    uow_a.__enter__()
    uow_b.__enter__()
    try:
        assert uow_a.idempotency.claim("post:e1") is True
        assert uow_b.idempotency.claim("post:e1") is True
        uow_a.idempotency.complete("post:e1")
        uow_b.idempotency.complete("post:e1")
        uow_a.commit()
        with pytest.raises(RevisionConflictError, match="Idempotency key"):
            uow_b.commit()
    finally:
        uow_a.__exit__(None, None, None)
        uow_b.__exit__(None, None, None)

    assert factory.store.idempotency["post:e1"] == "completed"
