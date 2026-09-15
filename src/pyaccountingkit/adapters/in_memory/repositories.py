"""In-memory repositories — behavioural reference of the repository ports."""

from __future__ import annotations

from collections.abc import Sequence

from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.core.errors import (
    EntryNotFoundError,
    JournalNotFoundError,
    PeriodNotFoundError,
    RevisionConflictError,
)
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.revisions import Revision
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod


class InMemoryJournalEntryRepository:
    """In-memory store of the JournalEntry aggregate with optimistic locking."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def add(self, entry: JournalEntry) -> None:
        if entry.id in self._store.entries:
            raise RevisionConflictError(f"Entry {entry.id} already exists: insert rejected")
        self._store.entries[entry.id] = entry
        self._store.entry_revisions[entry.id] = Revision()

    def save(self, entry: JournalEntry, expected_revision: Revision) -> None:
        current = self._store.entry_revisions.get(entry.id)
        if current is None or current != expected_revision:
            raise RevisionConflictError(
                f"Entry {entry.id}: expected revision {expected_revision}, current {current}"
            )
        self._store.entries[entry.id] = entry
        self._store.entry_revisions[entry.id] = expected_revision.incremented()

    def get(self, entry_id: EntryId) -> JournalEntry:
        if entry_id not in self._store.entries:
            raise EntryNotFoundError(f"Entry {entry_id} not found")
        return self._store.entries[entry_id]

    def get_revision(self, entry_id: EntryId) -> Revision:
        if entry_id not in self._store.entry_revisions:
            raise EntryNotFoundError(f"Entry {entry_id} has no revision")
        return self._store.entry_revisions[entry_id]

    def list_by_period(self, period_id: PeriodId) -> Sequence[JournalEntry]:
        return tuple(
            entry
            for entry in self._store.entries.values()
            if entry.period_id == period_id and entry.status is EntryStatus.POSTED
        )

    def list_by_journal(self, journal_id: JournalId) -> Sequence[JournalEntry]:
        return tuple(
            entry
            for entry in self._store.entries.values()
            if entry.journal_id == journal_id and entry.status is EntryStatus.POSTED
        )

    def find_by_reversal_of(self, entry_id: EntryId) -> Sequence[JournalEntry]:
        return tuple(
            entry for entry in self._store.entries.values() if entry.reversal_of_id == entry_id
        )


class InMemoryPeriodRepository:
    """In-memory store of accounting periods."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def add(self, period: AccountingPeriod) -> None:
        if period.id in self._store.periods:
            raise RevisionConflictError(f"Period {period.id} already exists")
        self._store.periods[period.id] = period

    def save(self, period: AccountingPeriod) -> None:
        self._store.periods[period.id] = period

    def get(self, period_id: PeriodId) -> AccountingPeriod:
        if period_id not in self._store.periods:
            raise PeriodNotFoundError(f"Period {period_id} not found")
        return self._store.periods[period_id]

    def list_all(self) -> Sequence[AccountingPeriod]:
        return tuple(self._store.periods[period_id] for period_id in sorted(self._store.periods))


class InMemoryJournalRepository:
    """In-memory store of journals."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def add(self, journal: Journal) -> None:
        if journal.id in self._store.journals:
            raise RevisionConflictError(f"Journal {journal.id} already exists")
        self._store.journals[journal.id] = journal

    def get(self, journal_id: JournalId) -> Journal:
        if journal_id not in self._store.journals:
            raise JournalNotFoundError(f"Journal {journal_id} not found")
        return self._store.journals[journal_id]


__all__ = [
    "InMemoryJournalEntryRepository",
    "InMemoryPeriodRepository",
    "InMemoryJournalRepository",
]
