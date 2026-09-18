"""Django repositories implementing PyAccountingKit persistence ports."""

from __future__ import annotations

from collections.abc import Sequence

from django.db import IntegrityError, transaction
from django.db.models import F

from pyaccountingkit.adapters.django.mappers import (
    entry_to_domain,
    entry_to_model,
    journal_to_domain,
    journal_to_model,
    line_to_model,
    period_to_domain,
    period_to_model,
)
from pyaccountingkit.adapters.django.models import (
    AccountingPeriodModel,
    AuditEventModel,
    IdempotencyRecordModel,
    JournalEntryModel,
    JournalLineModel,
    JournalModel,
    OutboxMessageModel,
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


class DjangoJournalEntryRepository:
    """PostgreSQL-backed JournalEntry repository with optimistic revisions."""

    def __init__(self, *, using: str = "default") -> None:
        self._using = using

    def add(self, entry: JournalEntry) -> None:
        model = entry_to_model(entry)
        try:
            with transaction.atomic(using=self._using):
                model.save(using=self._using, force_insert=True)
                JournalLineModel.objects.using(self._using).bulk_create(
                    [
                        line_to_model(str(entry.id), line_number, line)
                        for line_number, line in enumerate(entry.lines, start=1)
                    ]
                )
        except IntegrityError as exc:
            raise RevisionConflictError(f"Entry {entry.id} already exists or conflicts") from exc

    def save(self, entry: JournalEntry, expected_revision: Revision) -> None:
        try:
            with transaction.atomic(using=self._using):
                updated = (
                    JournalEntryModel.objects.using(self._using)
                    .filter(pk=str(entry.id), revision=int(expected_revision))
                    .update(
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
                        revision=F("revision") + 1,
                    )
                )
                if updated != 1:
                    raise RevisionConflictError(
                        f"Entry {entry.id}: expected revision {expected_revision}"
                    )
                JournalLineModel.objects.using(self._using).filter(
                    entry_id=str(entry.id)
                ).delete()
                JournalLineModel.objects.using(self._using).bulk_create(
                    [
                        line_to_model(str(entry.id), line_number, line)
                        for line_number, line in enumerate(entry.lines, start=1)
                    ]
                )
        except IntegrityError as exc:
            raise RevisionConflictError(f"Entry {entry.id} persistence conflict") from exc

    def get(self, entry_id: EntryId) -> JournalEntry:
        try:
            model = JournalEntryModel.objects.using(self._using).get(pk=str(entry_id))
        except JournalEntryModel.DoesNotExist as exc:
            raise EntryNotFoundError(f"Entry {entry_id} not found") from exc
        return entry_to_domain(model, using=self._using)

    def get_for_update(self, entry_id: EntryId) -> JournalEntry:
        """Load an entry under a PostgreSQL row lock inside an active transaction."""

        try:
            model = (
                JournalEntryModel.objects.using(self._using)
                .select_for_update()
                .get(pk=str(entry_id))
            )
        except JournalEntryModel.DoesNotExist as exc:
            raise EntryNotFoundError(f"Entry {entry_id} not found") from exc
        return entry_to_domain(model, using=self._using)

    def get_revision(self, entry_id: EntryId) -> Revision:
        value = (
            JournalEntryModel.objects.using(self._using)
            .filter(pk=str(entry_id))
            .values_list("revision", flat=True)
            .first()
        )
        if value is None:
            raise EntryNotFoundError(f"Entry {entry_id} has no revision")
        return Revision(int(value))

    def list_by_period(self, period_id: PeriodId) -> Sequence[JournalEntry]:
        rows = (
            JournalEntryModel.objects.using(self._using)
            .filter(period_id=str(period_id), status=EntryStatus.POSTED.value)
            .order_by("entry_date", "id")
        )
        return tuple(entry_to_domain(row, using=self._using) for row in rows)

    def list_by_journal(self, journal_id: JournalId) -> Sequence[JournalEntry]:
        rows = (
            JournalEntryModel.objects.using(self._using)
            .filter(journal_id=str(journal_id), status=EntryStatus.POSTED.value)
            .order_by("entry_date", "id")
        )
        return tuple(entry_to_domain(row, using=self._using) for row in rows)

    def find_by_reversal_of(self, entry_id: EntryId) -> Sequence[JournalEntry]:
        rows = (
            JournalEntryModel.objects.using(self._using)
            .filter(reversal_of_id=str(entry_id))
            .order_by("entry_date", "id")
        )
        return tuple(entry_to_domain(row, using=self._using) for row in rows)


class DjangoPeriodRepository:
    """PostgreSQL-backed accounting period repository."""

    def __init__(self, *, using: str = "default") -> None:
        self._using = using

    def add(self, period: AccountingPeriod) -> None:
        try:
            period_to_model(period).save(using=self._using, force_insert=True)
        except IntegrityError as exc:
            raise RevisionConflictError(f"Period {period.id} already exists or conflicts") from exc

    def save(self, period: AccountingPeriod) -> None:
        updated = (
            AccountingPeriodModel.objects.using(self._using)
            .filter(pk=str(period.id))
            .update(
                entity_id=str(period.entity_id),
                fiscal_year_id=str(period.fiscal_year_id),
                start_date=period.start_date,
                end_date=period.end_date,
                status=period.status.value,
            )
        )
        if updated != 1:
            raise PeriodNotFoundError(f"Period {period.id} not found")

    def get(self, period_id: PeriodId) -> AccountingPeriod:
        try:
            model = AccountingPeriodModel.objects.using(self._using).get(pk=str(period_id))
        except AccountingPeriodModel.DoesNotExist as exc:
            raise PeriodNotFoundError(f"Period {period_id} not found") from exc
        return period_to_domain(model)

    def get_for_update(self, period_id: PeriodId) -> AccountingPeriod:
        """Load a period under a PostgreSQL row lock inside an active transaction."""

        try:
            model = (
                AccountingPeriodModel.objects.using(self._using)
                .select_for_update()
                .get(pk=str(period_id))
            )
        except AccountingPeriodModel.DoesNotExist as exc:
            raise PeriodNotFoundError(f"Period {period_id} not found") from exc
        return period_to_domain(model)

    def list_all(self) -> Sequence[AccountingPeriod]:
        rows = AccountingPeriodModel.objects.using(self._using).order_by("start_date", "id")
        return tuple(period_to_domain(row) for row in rows)


class DjangoJournalRepository:
    """PostgreSQL-backed journal repository."""

    def __init__(self, *, using: str = "default") -> None:
        self._using = using

    def add(self, journal: Journal) -> None:
        try:
            journal_to_model(journal).save(using=self._using, force_insert=True)
        except IntegrityError as exc:
            raise RevisionConflictError(f"Journal {journal.id} already exists or conflicts") from exc

    def get(self, journal_id: JournalId) -> Journal:
        try:
            model = JournalModel.objects.using(self._using).get(pk=str(journal_id))
        except JournalModel.DoesNotExist as exc:
            raise JournalNotFoundError(f"Journal {journal_id} not found") from exc
        return journal_to_domain(model)


class DjangoAuditLogSink:
    """Persist audit events inside the active Django transaction."""

    def __init__(self, *, using: str = "default") -> None:
        self._using = using

    def record(self, event: AuditEvent) -> None:
        AuditEventModel.objects.using(self._using).create(
            event_type=event.event_type,
            entity_id=event.entity_id,
            actor_id=event.actor_id,
            occurred_at=event.occurred_at,
            payload=dict(event.payload),
        )


class DjangoIdempotencyStore:
    """Claim idempotency keys atomically with a unique PostgreSQL primary key."""

    def __init__(self, *, using: str = "default") -> None:
        self._using = using

    def claim(self, key: str) -> bool:
        try:
            with transaction.atomic(using=self._using):
                IdempotencyRecordModel.objects.using(self._using).create(
                    key=key,
                    status="claimed",
                )
        except IntegrityError:
            return False
        return True

    def complete(self, key: str) -> None:
        IdempotencyRecordModel.objects.using(self._using).update_or_create(
            key=key,
            defaults={"status": "completed"},
        )


class DjangoOutboxPublisher:
    """Persist outbox records in the same transaction as accounting changes."""

    def __init__(self, *, using: str = "default") -> None:
        self._using = using

    def publish(self, record: OutboxRecord) -> None:
        OutboxMessageModel.objects.using(self._using).create(
            event_type=record.event_type,
            entity_id=record.entity_id,
            payload=dict(record.payload),
            idempotency_key=record.idempotency_key,
        )


__all__ = [
    "DjangoAuditLogSink",
    "DjangoIdempotencyStore",
    "DjangoJournalEntryRepository",
    "DjangoJournalRepository",
    "DjangoOutboxPublisher",
    "DjangoPeriodRepository",
]
