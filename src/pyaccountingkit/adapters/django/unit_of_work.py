"""Django transaction boundary implementing the public UnitOfWork contract."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

from django.db import transaction

from pyaccountingkit.adapters.django.repositories import (
    DjangoAuditLogSink,
    DjangoIdempotencyStore,
    DjangoJournalEntryRepository,
    DjangoJournalRepository,
    DjangoOutboxPublisher,
    DjangoPeriodRepository,
)
from pyaccountingkit.core.clock import ClockProtocol, SystemClock


class DjangoUnitOfWork:
    """Bind PyAccountingKit repositories to one Django transaction.atomic scope."""

    def __init__(
        self,
        *,
        using: str = "default",
        clock: ClockProtocol | None = None,
    ) -> None:
        self.using = using
        self.clock = clock if clock is not None else SystemClock()
        self.entries = DjangoJournalEntryRepository(using=using)
        self.periods = DjangoPeriodRepository(using=using)
        self.journals = DjangoJournalRepository(using=using)
        self.audit = DjangoAuditLogSink(using=using)
        self.idempotency = DjangoIdempotencyStore(using=using)
        self.outbox = DjangoOutboxPublisher(using=using)
        self._atomic: Any = None
        self._entered = False
        self._committed = False
        self._rolled_back = False

    def __enter__(self) -> Self:
        if self._entered:
            raise RuntimeError("DjangoUnitOfWork cannot be re-entered")
        self._atomic = transaction.atomic(using=self.using)
        self._atomic.__enter__()
        self._entered = True
        self._committed = False
        self._rolled_back = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if not self._entered:
            return
        if exc_type is not None or not self._committed or self._rolled_back:
            transaction.set_rollback(True, using=self.using)
        atomic = self._atomic
        try:
            atomic.__exit__(exc_type, exc, tb)
        finally:
            self._atomic = None
            self._entered = False
            self._committed = False
            self._rolled_back = False

    def commit(self) -> None:
        """Mark the active atomic block for commit when its context exits."""

        if not self._entered:
            raise RuntimeError("Cannot commit an un-entered DjangoUnitOfWork")
        if self._rolled_back:
            raise RuntimeError("Cannot commit a DjangoUnitOfWork marked for rollback")
        self._committed = True

    def rollback(self) -> None:
        """Mark the active transaction rollback-only."""

        if not self._entered:
            return
        transaction.set_rollback(True, using=self.using)
        self._rolled_back = True
        self._committed = False


class DjangoUnitOfWorkFactory:
    """Open fresh Django UnitOfWork scopes against one configured database alias."""

    def __init__(
        self,
        *,
        using: str = "default",
        clock: ClockProtocol | None = None,
    ) -> None:
        self._using = using
        self._clock = clock

    def open(self) -> DjangoUnitOfWork:
        return DjangoUnitOfWork(using=self._using, clock=self._clock)


__all__ = ["DjangoUnitOfWork", "DjangoUnitOfWorkFactory"]
