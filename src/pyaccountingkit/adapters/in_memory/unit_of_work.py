"""In-memory UnitOfWork — isolated reference transaction boundary.

Each entered UnitOfWork operates on a detached working copy. Commit validates
that every touched key still matches the baseline observed at entry, then
merges only the local delta into the shared store. Rollback therefore never
restores an old global snapshot and cannot erase another transaction's commit.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from pyaccountingkit.adapters.in_memory.repositories import (
    InMemoryJournalEntryRepository,
    InMemoryJournalRepository,
    InMemoryPeriodRepository,
)
from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.core.clock import ClockProtocol, SystemClock
from pyaccountingkit.core.errors import RevisionConflictError
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.ports.outbox import OutboxRecord


class InMemoryAuditLogSink:
    """Append audit events to the transaction-local working store."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def record(self, event: AuditEvent) -> None:
        self._store.audit_log.append(event)


class InMemoryIdempotencyStore:
    """Claim and complete idempotency keys in transaction-local state."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def claim(self, key: str) -> bool:
        if key in self._store.idempotency:
            return False
        self._store.idempotency[key] = "claimed"
        return True

    def complete(self, key: str) -> None:
        self._store.idempotency[key] = "completed"


class InMemoryOutboxPublisher:
    """Append outbox records to the transaction-local working store."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def publish(self, record: OutboxRecord) -> None:
        self._store.outbox.append(record)


class InMemoryUnitOfWork:
    """Transactionally isolated scope over one shared ``InMemoryStore``."""

    def __init__(
        self,
        store: InMemoryStore,
        clock: ClockProtocol | None = None,
    ) -> None:
        self._store = store
        self.clock = clock if clock is not None else SystemClock()
        self._baseline: InMemoryStore | None = None
        self._working = store.copy()
        self._committed = False
        self._bind(self._working)

    def _bind(self, store: InMemoryStore) -> None:
        self.entries = InMemoryJournalEntryRepository(store)
        self.periods = InMemoryPeriodRepository(store)
        self.journals = InMemoryJournalRepository(store)
        self.audit = InMemoryAuditLogSink(store)
        self.idempotency = InMemoryIdempotencyStore(store)
        self.outbox = InMemoryOutboxPublisher(store)

    def __enter__(self) -> Self:
        self._baseline = self._store.copy()
        self._working = self._baseline.copy()
        self._bind(self._working)
        self._committed = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None or not self._committed:
            self.rollback()

    def commit(self) -> None:
        baseline = self._baseline
        if baseline is None:
            raise RuntimeError("Cannot commit an un-entered UnitOfWork")
        self._validate_concurrent_changes(baseline)
        self._merge_delta(baseline)
        self._baseline = None
        self._committed = True

    def rollback(self) -> None:
        """Discard local state without mutating the shared store."""
        self._baseline = None
        self._working = self._store.copy()
        self._bind(self._working)
        self._committed = False

    def _validate_concurrent_changes(self, baseline: InMemoryStore) -> None:
        for entry_id in set(baseline.entries) | set(self._working.entries):
            changed = (
                baseline.entries.get(entry_id) != self._working.entries.get(entry_id)
                or baseline.entry_revisions.get(entry_id)
                != self._working.entry_revisions.get(entry_id)
            )
            if changed and (
                self._store.entries.get(entry_id) != baseline.entries.get(entry_id)
                or self._store.entry_revisions.get(entry_id)
                != baseline.entry_revisions.get(entry_id)
            ):
                raise RevisionConflictError(
                    f"Entry {entry_id} changed after UnitOfWork snapshot"
                )

        self._validate_mapping_changes(
            "Period",
            baseline.periods,
            self._working.periods,
            self._store.periods,
        )
        self._validate_mapping_changes(
            "Journal",
            baseline.journals,
            self._working.journals,
            self._store.journals,
        )
        self._validate_mapping_changes(
            "Idempotency key",
            baseline.idempotency,
            self._working.idempotency,
            self._store.idempotency,
        )

        if self._working.audit_log[: len(baseline.audit_log)] != baseline.audit_log:
            raise RevisionConflictError("audit log prefix changed inside UnitOfWork")
        if self._working.outbox[: len(baseline.outbox)] != baseline.outbox:
            raise RevisionConflictError("outbox prefix changed inside UnitOfWork")

    @staticmethod
    def _validate_mapping_changes(
        resource: str,
        baseline: dict[object, object],
        working: dict[object, object],
        shared: dict[object, object],
    ) -> None:
        for key in set(baseline) | set(working):
            if baseline.get(key) != working.get(key) and shared.get(key) != baseline.get(key):
                raise RevisionConflictError(f"{resource} {key} changed after UnitOfWork snapshot")

    def _merge_delta(self, baseline: InMemoryStore) -> None:
        self._merge_mapping(baseline.entries, self._working.entries, self._store.entries)
        self._merge_mapping(
            baseline.entry_revisions,
            self._working.entry_revisions,
            self._store.entry_revisions,
        )
        self._merge_mapping(baseline.periods, self._working.periods, self._store.periods)
        self._merge_mapping(baseline.journals, self._working.journals, self._store.journals)
        self._merge_mapping(
            baseline.idempotency,
            self._working.idempotency,
            self._store.idempotency,
        )
        self._store.audit_log.extend(self._working.audit_log[len(baseline.audit_log) :])
        self._store.outbox.extend(self._working.outbox[len(baseline.outbox) :])

    @staticmethod
    def _merge_mapping(
        baseline: dict[object, object],
        working: dict[object, object],
        shared: dict[object, object],
    ) -> None:
        for key in set(baseline) | set(working):
            if baseline.get(key) == working.get(key):
                continue
            if key in working:
                shared[key] = working[key]
            else:
                shared.pop(key, None)


class InMemoryUnitOfWorkFactory:
    """Open fresh isolated transaction scopes over one shared store."""

    def __init__(self, store: InMemoryStore | None = None) -> None:
        self._store = store if store is not None else InMemoryStore()

    @property
    def store(self) -> InMemoryStore:
        return self._store

    def open(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(self._store)


__all__ = [
    "InMemoryUnitOfWork",
    "InMemoryUnitOfWorkFactory",
    "InMemoryAuditLogSink",
    "InMemoryIdempotencyStore",
    "InMemoryOutboxPublisher",
]
