"""Repository ports — persistence contracts over domain objects only.

Repositories expose and accept domain aggregate objects; DB-specific
representation never leaks through these protocols.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.revisions import Revision
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod


class JournalEntryRepositoryProtocol(Protocol):
    """Persistence contract for the JournalEntry aggregate."""

    def add(self, entry: JournalEntry) -> None:
        """Insert a new entry at its base revision."""
        ...

    def save(self, entry: JournalEntry, expected_revision: Revision) -> None:
        """Persist a mutation, refusing a stale expected revision."""
        ...

    def get(self, entry_id: EntryId) -> JournalEntry:
        """Return the entry by id, or raise EntryNotFoundError."""
        ...

    def get_revision(self, entry_id: EntryId) -> Revision:
        """Return the current optimistic-lock revision of an entry."""
        ...

    def list_by_period(self, period_id: PeriodId) -> Sequence[JournalEntry]:
        """Return posted entries of a period in chronological order."""
        ...

    def list_by_journal(self, journal_id: JournalId) -> Sequence[JournalEntry]:
        """Return posted entries of a journal in chronological order."""
        ...

    def find_by_reversal_of(self, entry_id: EntryId) -> Sequence[JournalEntry]:
        """Return entries recorded as the reversal of *entry_id*."""
        ...


class PeriodRepositoryProtocol(Protocol):
    """Persistence contract for accounting periods."""

    def add(self, period: AccountingPeriod) -> None:
        """Insert a new period."""
        ...

    def save(self, period: AccountingPeriod) -> None:
        """Persist a status-only update of an existing period."""
        ...

    def get(self, period_id: PeriodId) -> AccountingPeriod:
        """Return the period by id, or raise PeriodNotFoundError."""
        ...

    def list_all(self) -> Sequence[AccountingPeriod]:
        """Return every registered period ordered by start date."""
        ...


class JournalRepositoryProtocol(Protocol):
    """Persistence contract for journals."""

    def add(self, journal: Journal) -> None:
        """Insert a new journal."""
        ...

    def get(self, journal_id: JournalId) -> Journal:
        """Return the journal by id, or raise JournalNotFoundError."""
        ...


__all__ = [
    "JournalEntryRepositoryProtocol",
    "PeriodRepositoryProtocol",
    "JournalRepositoryProtocol",
]
