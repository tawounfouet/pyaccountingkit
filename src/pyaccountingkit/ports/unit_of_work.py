"""Unit-of-Work ports — the transaction boundary over repositories.

A UnitOfWork groups one or more repository mutations behind a single
commit that is atomic, and a rollback that leaves no partial state.
"""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.ports.audit import AuditLogSinkProtocol
from pyaccountingkit.ports.idempotency import IdempotencyStoreProtocol
from pyaccountingkit.ports.outbox import OutboxPublisherProtocol
from pyaccountingkit.ports.repositories import (
    JournalEntryRepositoryProtocol,
    JournalRepositoryProtocol,
    PeriodRepositoryProtocol,
)


class UnitOfWorkProtocol(Protocol):
    """Transactional unit grouping every repository behind one commit."""

    entries: JournalEntryRepositoryProtocol
    periods: PeriodRepositoryProtocol
    journals: JournalRepositoryProtocol
    audit: AuditLogSinkProtocol
    idempotency: IdempotencyStoreProtocol
    outbox: OutboxPublisherProtocol
    clock: ClockProtocol

    def __enter__(self) -> UnitOfWorkProtocol: ...
    def __exit__(self, exc_type: object, exc: object, tb: object) -> None: ...
    def commit(self) -> None:
        """Atomically publish all buffered mutations."""
        ...

    def rollback(self) -> None:
        """Discard every buffered mutation."""
        ...


class UnitOfWorkFactoryProtocol(Protocol):
    """Supplies fresh, bound transaction scopes."""

    def open(self) -> UnitOfWorkProtocol:
        """Open a new UnitOfWork over the underlying store."""
        ...


__all__ = ["UnitOfWorkProtocol", "UnitOfWorkFactoryProtocol"]
