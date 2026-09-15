"""In-memory UnitOfWork — the reference transaction boundary.

Mutations inside a UnitOfWork are staged in the shared InMemoryStore; a
snapshot taken on __enter__ makes rollback atomic and complete.
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
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.ports.outbox import OutboxRecord


class InMemoryAuditLogSink:
    """Appends AuditEvent records to the shared store."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def record(self, event: AuditEvent) -> None:
        self._store.audit_log.append(event)


class InMemoryIdempotencyStore:
    """Claims and completes idempotency keys in the shared store."""

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
    """Stages OutboxRecords that become visible after commit."""

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def publish(self, record: OutboxRecord) -> None:
        self._store.outbox.append(record)


class InMemoryUnitOfWork:
    """Transactional scope over a shared InMemoryStore."""

    def __init__(
        self,
        store: InMemoryStore,
        clock: ClockProtocol | None = None,
    ) -> None:
        self._store = store
        self.clock = clock if clock is not None else SystemClock()
        self.entries = InMemoryJournalEntryRepository(store)
        self.periods = InMemoryPeriodRepository(store)
        self.journals = InMemoryJournalRepository(store)
        self.audit = InMemoryAuditLogSink(store)
        self.idempotency = InMemoryIdempotencyStore(store)
        self.outbox = InMemoryOutboxPublisher(store)
        self._snapshot: InMemoryStore | None = None
        self._committed = False

    def __enter__(self) -> Self:
        self._snapshot = self._store.copy()
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
        if self._snapshot is None:
            raise RuntimeError("Cannot commit an un-entered UnitOfWork")
        self._snapshot = None
        self._committed = True

    def rollback(self) -> None:
        if self._snapshot is not None:
            self._store.restore(self._snapshot)
            self._snapshot = None
        self._committed = False


class InMemoryUnitOfWorkFactory:
    """Opens fresh transaction scopes over one shared InMemoryStore."""

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
