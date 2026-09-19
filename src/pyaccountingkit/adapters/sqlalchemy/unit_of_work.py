"""SQLAlchemy Session transaction boundary implementing the public UnitOfWork contract."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, SessionTransaction, sessionmaker

from pyaccountingkit.adapters.sqlalchemy.repositories import (
    SQLAlchemyAuditLogSink,
    SQLAlchemyIdempotencyStore,
    SQLAlchemyJournalEntryRepository,
    SQLAlchemyJournalRepository,
    SQLAlchemyOutboxPublisher,
    SQLAlchemyPeriodRepository,
)
from pyaccountingkit.core.clock import ClockProtocol, SystemClock


class SessionUnitOfWork:
    """Bind repositories to one SQLAlchemy Session transaction."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        clock: ClockProtocol | None = None,
    ) -> None:
        self.clock = clock if clock is not None else SystemClock()
        self.session = session_factory()
        self.entries = SQLAlchemyJournalEntryRepository(self.session)
        self.periods = SQLAlchemyPeriodRepository(self.session)
        self.journals = SQLAlchemyJournalRepository(self.session)
        self.audit = SQLAlchemyAuditLogSink(self.session)
        self.idempotency = SQLAlchemyIdempotencyStore(self.session)
        self.outbox = SQLAlchemyOutboxPublisher(self.session)
        self._transaction: SessionTransaction | None = None
        self._entered = False
        self._committed = False
        self._rolled_back = False

    def __enter__(self) -> Self:
        if self._entered:
            raise RuntimeError("SessionUnitOfWork cannot be re-entered")
        self._transaction = self.session.begin()
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
        transaction = self._transaction
        try:
            if transaction is not None and transaction.is_active:
                if exc_type is not None or not self._committed or self._rolled_back:
                    transaction.rollback()
                else:
                    transaction.commit()
        finally:
            self.session.close()
            self._transaction = None
            self._entered = False
            self._committed = False
            self._rolled_back = False

    def commit(self) -> None:
        """Mark the current Session transaction for commit on context exit."""

        if not self._entered:
            raise RuntimeError("Cannot commit an un-entered SessionUnitOfWork")
        if self._rolled_back:
            raise RuntimeError("Cannot commit a SessionUnitOfWork marked for rollback")
        self._committed = True

    def rollback(self) -> None:
        """Mark the current Session transaction rollback-only."""

        if not self._entered:
            return
        self._rolled_back = True
        self._committed = False


class SQLAlchemyUnitOfWorkFactory:
    """Open fresh SessionUnitOfWork scopes from one SQLAlchemy Engine."""

    def __init__(
        self,
        engine: Engine,
        *,
        clock: ClockProtocol | None = None,
    ) -> None:
        self._session_factory = sessionmaker(
            bind=engine,
            class_=Session,
            expire_on_commit=False,
        )
        self._clock = clock

    def open(self) -> SessionUnitOfWork:
        return SessionUnitOfWork(self._session_factory, clock=self._clock)


__all__ = ["SQLAlchemyUnitOfWorkFactory", "SessionUnitOfWork"]
