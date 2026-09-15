"""In-memory reference store for behaviour qualification.

This adapter is the behavioural reference of the persistence contract but
does NOT qualify production: it is single-threaded and keeps everything in
memory.  Production adapters (PostgreSQL/SQLAlchemy) implement the same
ports with real transactional guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.revisions import Revision
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.ports.outbox import OutboxRecord


@dataclass(slots=True)
class InMemoryStore:
    """State shared by every in-memory UnitOfWork bound to it."""

    entries: dict[EntryId, JournalEntry] = field(default_factory=dict)
    entry_revisions: dict[EntryId, Revision] = field(default_factory=dict)
    periods: dict[PeriodId, AccountingPeriod] = field(default_factory=dict)
    journals: dict[JournalId, Journal] = field(default_factory=dict)
    idempotency: dict[str, str] = field(default_factory=dict)
    outbox: list[OutboxRecord] = field(default_factory=list)
    audit_log: list[AuditEvent] = field(default_factory=list)

    def copy(self) -> InMemoryStore:
        """Return a detached copy used as a rollback snapshot."""
        return InMemoryStore(
            entries=dict(self.entries),
            entry_revisions=dict(self.entry_revisions),
            periods=dict(self.periods),
            journals=dict(self.journals),
            idempotency=dict(self.idempotency),
            outbox=list(self.outbox),
            audit_log=list(self.audit_log),
        )

    def restore(self, snapshot: InMemoryStore) -> None:
        """Roll back this store to a previously taken snapshot."""
        self.entries = dict(snapshot.entries)
        self.entry_revisions = dict(snapshot.entry_revisions)
        self.periods = dict(snapshot.periods)
        self.journals = dict(snapshot.journals)
        self.idempotency = dict(snapshot.idempotency)
        self.outbox = list(snapshot.outbox)
        self.audit_log = list(snapshot.audit_log)

    def drain_outbox(self) -> list[OutboxRecord]:
        """Collect and clear every published outbox message."""
        messages = list(self.outbox)
        self.outbox.clear()
        return messages


__all__ = ["InMemoryStore"]
