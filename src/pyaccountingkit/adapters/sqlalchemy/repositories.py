"""SQLAlchemy repositories implementing PyAccountingKit persistence ports."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pyaccountingkit.adapters.sqlalchemy.mappers import (
    entry_to_domain,
    entry_to_table,
    journal_to_domain,
    journal_to_table,
    line_to_table,
    period_to_domain,
    period_to_table,
)
from pyaccountingkit.adapters.sqlalchemy.tables import (
    AccountingPeriodTable,
    AuditEventTable,
    IdempotencyRecordTable,
    JournalEntryTable,
    JournalLineTable,
    JournalTable,
    OutboxMessageTable,
)
from pyaccountingkit.core.errors import (
    EntryNotFoundError,
    JournalNotFoundError,
    PeriodNotFoundError,
    RevisionConflictError,
)
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.revisions import Revision
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.ports.outbox import OutboxRecord


class SQLAlchemyJournalEntryRepository:
    """Session-bound JournalEntry repository with pessimistic reads and optimistic saves."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entry: JournalEntry) -> None:
        self._session.add(entry_to_table(entry))
        self._session.add_all(
            [
                line_to_table(str(entry.id), line_number, line)
                for line_number, line in enumerate(entry.lines, start=1)
            ]
        )
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise RevisionConflictError(f"Entry {entry.id} already exists or conflicts") from exc

    def save(self, entry: JournalEntry, expected_revision: Revision) -> None:
        try:
            result = self._session.execute(
                update(JournalEntryTable)
                .where(
                    JournalEntryTable.id == str(entry.id),
                    JournalEntryTable.revision == int(expected_revision),
                )
                .values(
                    journal_id=str(entry.journal_id),
                    period_id=str(entry.period_id),
                    entry_date=entry.entry_date,
                    description=entry.description,
                    status=entry.status.value,
                    posted_at=entry.posted_at,
                    reversal_of_id=(
                        str(entry.reversal_of_id) if entry.reversal_of_id is not None else None
                    ),
                    reversed_by_id=(
                        str(entry.reversed_by_id) if entry.reversed_by_id is not None else None
                    ),
                    revision=JournalEntryTable.revision + 1,
                )
                .execution_options(synchronize_session=False)
            )
            if result.rowcount != 1:
                raise RevisionConflictError(
                    f"Entry {entry.id}: expected revision {expected_revision}"
                )
            self._session.execute(
                delete(JournalLineTable)
                .where(JournalLineTable.entry_id == str(entry.id))
                .execution_options(synchronize_session=False)
            )
            self._session.add_all(
                [
                    line_to_table(str(entry.id), line_number, line)
                    for line_number, line in enumerate(entry.lines, start=1)
                ]
            )
            self._session.flush()
        except IntegrityError as exc:
            raise RevisionConflictError(f"Entry {entry.id} persistence conflict") from exc

    def get(self, entry_id: EntryId) -> JournalEntry:
        row = self._session.scalar(
            select(JournalEntryTable)
            .where(JournalEntryTable.id == str(entry_id))
            .with_for_update()
        )
        if row is None:
            raise EntryNotFoundError(f"Entry {entry_id} not found")
        return entry_to_domain(self._session, row)

    def get_for_update(self, entry_id: EntryId) -> JournalEntry:
        return self.get(entry_id)

    def get_revision(self, entry_id: EntryId) -> Revision:
        value = self._session.scalar(
            select(JournalEntryTable.revision).where(JournalEntryTable.id == str(entry_id))
        )
        if value is None:
            raise EntryNotFoundError(f"Entry {entry_id} has no revision")
        return Revision(value)

    def list_by_period(self, period_id: PeriodId) -> Sequence[JournalEntry]:
        rows = self._session.scalars(
            select(JournalEntryTable)
            .where(
                JournalEntryTable.period_id == str(period_id),
                JournalEntryTable.status == EntryStatus.POSTED.value,
            )
            .order_by(JournalEntryTable.entry_date, JournalEntryTable.id)
        )
        return tuple(entry_to_domain(self._session, row) for row in rows)

    def list_by_journal(self, journal_id: JournalId) -> Sequence[JournalEntry]:
        rows = self._session.scalars(
            select(JournalEntryTable)
            .where(
                JournalEntryTable.journal_id == str(journal_id),
                JournalEntryTable.status == EntryStatus.POSTED.value,
            )
            .order_by(JournalEntryTable.entry_date, JournalEntryTable.id)
        )
        return tuple(entry_to_domain(self._session, row) for row in rows)

    def find_by_reversal_of(self, entry_id: EntryId) -> Sequence[JournalEntry]:
        rows = self._session.scalars(
            select(JournalEntryTable)
            .where(JournalEntryTable.reversal_of_id == str(entry_id))
            .order_by(JournalEntryTable.entry_date, JournalEntryTable.id)
        )
        return tuple(entry_to_domain(self._session, row) for row in rows)


class SQLAlchemyPeriodRepository:
    """Session-bound accounting period repository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, period: AccountingPeriod) -> None:
        self._session.add(period_to_table(period))
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise RevisionConflictError(f"Period {period.id} already exists or conflicts") from exc

    def save(self, period: AccountingPeriod) -> None:
        result = self._session.execute(
            update(AccountingPeriodTable)
            .where(AccountingPeriodTable.id == str(period.id))
            .values(
                entity_id=str(period.entity_id),
                fiscal_year_id=str(period.fiscal_year_id),
                start_date=period.start_date,
                end_date=period.end_date,
                status=period.status.value,
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise PeriodNotFoundError(f"Period {period.id} not found")

    def get(self, period_id: PeriodId) -> AccountingPeriod:
        row = self._session.scalar(
            select(AccountingPeriodTable)
            .where(AccountingPeriodTable.id == str(period_id))
            .with_for_update()
        )
        if row is None:
            raise PeriodNotFoundError(f"Period {period_id} not found")
        return period_to_domain(row)

    def get_for_update(self, period_id: PeriodId) -> AccountingPeriod:
        return self.get(period_id)

    def list_all(self) -> Sequence[AccountingPeriod]:
        rows = self._session.scalars(
            select(AccountingPeriodTable).order_by(
                AccountingPeriodTable.start_date,
                AccountingPeriodTable.id,
            )
        )
        return tuple(period_to_domain(row) for row in rows)


class SQLAlchemyJournalRepository:
    """Session-bound journal repository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, journal: Journal) -> None:
        self._session.add(journal_to_table(journal))
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise RevisionConflictError(
                f"Journal {journal.id} already exists or conflicts"
            ) from exc

    def get(self, journal_id: JournalId) -> Journal:
        row = self._session.get(JournalTable, str(journal_id))
        if row is None:
            raise JournalNotFoundError(f"Journal {journal_id} not found")
        return journal_to_domain(row)


class SQLAlchemyAuditLogSink:
    """Persist audit records in the enclosing Session transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, event: AuditEvent) -> None:
        self._session.add(
            AuditEventTable(
                event_type=event.event_type,
                entity_id=event.entity_id,
                actor_id=event.actor_id,
                occurred_at=event.occurred_at,
                payload=dict(event.payload),
            )
        )


class SQLAlchemyIdempotencyStore:
    """Claim idempotency keys through a PostgreSQL uniqueness constraint."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def claim(self, key: str) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(IdempotencyRecordTable(key=key, status="claimed"))
                self._session.flush()
        except IntegrityError:
            return False
        return True

    def complete(self, key: str) -> None:
        row = self._session.get(IdempotencyRecordTable, key)
        if row is None:
            self._session.add(IdempotencyRecordTable(key=key, status="completed"))
        else:
            row.status = "completed"


class SQLAlchemyOutboxPublisher:
    """Persist outbox records in the same Session transaction as accounting mutations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def publish(self, record: OutboxRecord) -> None:
        self._session.add(
            OutboxMessageTable(
                event_type=record.event_type,
                entity_id=record.entity_id,
                payload=dict(record.payload),
                idempotency_key=record.idempotency_key,
            )
        )


__all__ = [
    "SQLAlchemyAuditLogSink",
    "SQLAlchemyIdempotencyStore",
    "SQLAlchemyJournalEntryRepository",
    "SQLAlchemyJournalRepository",
    "SQLAlchemyOutboxPublisher",
    "SQLAlchemyPeriodRepository",
]
