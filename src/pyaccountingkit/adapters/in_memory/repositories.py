"""In-memory repositories — behavioural reference of the repository ports."""

from __future__ import annotations

from collections.abc import Callable, Sequence

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
from pyaccountingkit.domain.traceability.accounting_execution import AccountingExecutionTrace


ReadTracker = Callable[[str, object], None]


class InMemoryJournalEntryRepository:
    """In-memory store of the JournalEntry aggregate with optimistic locking."""

    def __init__(
        self,
        store: InMemoryStore,
        on_read: ReadTracker | None = None,
    ) -> None:
        self._store = store
        self._on_read = on_read

    def _track(self, kind: str, key: object) -> None:
        if self._on_read is not None:
            self._on_read(kind, key)

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
        persisted = self._store.entries.get(entry.id)
        if persisted is None:
            raise RevisionConflictError(f"Entry {entry.id}: persisted value is missing")
        persisted.assert_persistence_successor(entry)
        self._store.entries[entry.id] = entry
        self._store.entry_revisions[entry.id] = expected_revision.incremented()

    def get(self, entry_id: EntryId) -> JournalEntry:
        self._track("entry", entry_id)
        if entry_id not in self._store.entries:
            raise EntryNotFoundError(f"Entry {entry_id} not found")
        return self._store.entries[entry_id]

    def get_revision(self, entry_id: EntryId) -> Revision:
        self._track("entry", entry_id)
        if entry_id not in self._store.entry_revisions:
            raise EntryNotFoundError(f"Entry {entry_id} has no revision")
        return self._store.entry_revisions[entry_id]

    def list_by_period(self, period_id: PeriodId) -> Sequence[JournalEntry]:
        self._track("entries_by_period", period_id)
        return tuple(
            entry
            for entry in self._store.entries.values()
            if entry.period_id == period_id
            and entry.status in {EntryStatus.POSTED, EntryStatus.REVERSED}
        )

    def list_by_journal(self, journal_id: JournalId) -> Sequence[JournalEntry]:
        self._track("entries_by_journal", journal_id)
        return tuple(
            entry
            for entry in self._store.entries.values()
            if entry.journal_id == journal_id
            and entry.status in {EntryStatus.POSTED, EntryStatus.REVERSED}
        )

    def find_by_reversal_of(self, entry_id: EntryId) -> Sequence[JournalEntry]:
        self._track("reversals_of", entry_id)
        return tuple(
            entry for entry in self._store.entries.values() if entry.reversal_of_id == entry_id
        )


class InMemoryAccountingExecutionTraceRepository:
    """Append-only in-memory execution trace repository."""

    def __init__(
        self,
        store: InMemoryStore,
        on_read: ReadTracker | None = None,
    ) -> None:
        self._store = store
        self._on_read = on_read

    def append(self, trace: AccountingExecutionTrace) -> None:
        existing = self._store.execution_traces.get(trace.journal_entry_id)
        if existing is not None:
            if existing == trace:
                return
            raise RevisionConflictError(
                f"Execution trace already exists for entry {trace.journal_entry_id}"
            )
        self._store.execution_traces[trace.journal_entry_id] = trace

    def get_by_entry_id(self, entry_id: EntryId) -> AccountingExecutionTrace | None:
        if self._on_read is not None:
            self._on_read("execution_trace", entry_id)
        return self._store.execution_traces.get(entry_id)


class InMemoryPeriodRepository:
    """In-memory store of accounting periods."""

    def __init__(
        self,
        store: InMemoryStore,
        on_read: ReadTracker | None = None,
    ) -> None:
        self._store = store
        self._on_read = on_read

    def add(self, period: AccountingPeriod) -> None:
        if period.id in self._store.periods:
            raise RevisionConflictError(f"Period {period.id} already exists")
        self._store.periods[period.id] = period

    def save(self, period: AccountingPeriod) -> None:
        persisted = self._store.periods.get(period.id)
        if persisted is None:
            raise PeriodNotFoundError(f"Period {period.id} not found")
        persisted.assert_persistence_successor(period)
        self._store.periods[period.id] = period

    def get(self, period_id: PeriodId) -> AccountingPeriod:
        if self._on_read is not None:
            self._on_read("period", period_id)
        if period_id not in self._store.periods:
            raise PeriodNotFoundError(f"Period {period_id} not found")
        return self._store.periods[period_id]

    def list_all(self) -> Sequence[AccountingPeriod]:
        if self._on_read is not None:
            self._on_read("periods_all", "*")
        return tuple(self._store.periods[period_id] for period_id in sorted(self._store.periods))


class InMemoryJournalRepository:
    """In-memory store of journals."""

    def __init__(
        self,
        store: InMemoryStore,
        on_read: ReadTracker | None = None,
    ) -> None:
        self._store = store
        self._on_read = on_read

    def add(self, journal: Journal) -> None:
        if journal.id in self._store.journals:
            raise RevisionConflictError(f"Journal {journal.id} already exists")
        self._store.journals[journal.id] = journal

    def get(self, journal_id: JournalId) -> Journal:
        if self._on_read is not None:
            self._on_read("journal", journal_id)
        if journal_id not in self._store.journals:
            raise JournalNotFoundError(f"Journal {journal_id} not found")
        return self._store.journals[journal_id]


__all__ = [
    "InMemoryAccountingExecutionTraceRepository",
    "InMemoryJournalEntryRepository",
    "InMemoryPeriodRepository",
    "InMemoryJournalRepository",
]
