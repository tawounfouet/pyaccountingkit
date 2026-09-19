"""Real PostgreSQL qualification for the optional Django adapter."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime

import pytest

if os.getenv("PYAK_POSTGRES_TEST") != "1":
    pytest.skip("PostgreSQL adapter qualification is disabled", allow_module_level=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.support.django_settings")

import django

django.setup()

from pyaccountingkit.adapters.django.models import (
    AccountingPeriodModel,
    AuditEventModel,
    IdempotencyRecordModel,
    JournalEntryModel,
    JournalLineModel,
    JournalModel,
    OutboxMessageModel,
)
from pyaccountingkit.adapters.django.unit_of_work import DjangoUnitOfWorkFactory
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import (
    AccountId,
    EntityId,
    EntryId,
    FiscalYearId,
    JournalId,
    PeriodId,
)
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.ports.outbox import OutboxRecord

NOW = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)
ENTITY = EntityId("entity:postgres")
JOURNAL_ID = JournalId("journal:sales")
PERIOD_ID = PeriodId("period:2026-09")


@pytest.fixture(autouse=True)
def clean_postgresql_adapter_tables() -> None:
    """Keep every test isolated while exercising the real migrated schema."""

    JournalLineModel.objects.all().delete()
    JournalEntryModel.objects.all().delete()
    OutboxMessageModel.objects.all().delete()
    AuditEventModel.objects.all().delete()
    IdempotencyRecordModel.objects.all().delete()
    AccountingPeriodModel.objects.all().delete()
    JournalModel.objects.all().delete()


def _journal() -> Journal:
    return Journal(
        id=JOURNAL_ID,
        entity_id=ENTITY,
        code="SAL",
        label="Sales",
    )


def _period() -> AccountingPeriod:
    return AccountingPeriod(
        id=PERIOD_ID,
        entity_id=ENTITY,
        fiscal_year_id=FiscalYearId("fy:2026"),
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
    )


def _entry(entry_id: str = "entry:1") -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JOURNAL_ID,
        period_id=PERIOD_ID,
        entry_date=date(2026, 9, 18),
        description="PostgreSQL adapter round-trip",
        lines=(
            JournalLine(
                account_id=AccountId("411000"),
                debit=Money.from_str("125.50", EUR),
                credit=Money.zero(EUR),
                label="Customer",
            ),
            JournalLine(
                account_id=AccountId("707000"),
                debit=Money.zero(EUR),
                credit=Money.from_str("125.50", EUR),
                label="Revenue",
            ),
        ),
    )


def test_repository_round_trip_is_exact() -> None:
    factory = DjangoUnitOfWorkFactory(clock=FrozenClock(NOW))
    journal = _journal()
    period = _period()
    entry = _entry()

    with factory.open() as uow:
        uow.journals.add(journal)
        uow.periods.add(period)
        uow.entries.add(entry)
        uow.commit()

    assert factory.open().journals.get(JOURNAL_ID) == journal
    assert factory.open().periods.get(PERIOD_ID) == period
    assert factory.open().entries.get(EntryId("entry:1")) == entry
    assert JournalLineModel.objects.filter(entry_id="entry:1").count() == 2


def test_uncommitted_unit_of_work_rolls_back_every_sink() -> None:
    factory = DjangoUnitOfWorkFactory(clock=FrozenClock(NOW))

    with factory.open() as uow:
        uow.journals.add(_journal())
        uow.periods.add(_period())
        uow.entries.add(_entry())
        assert uow.idempotency.claim("post:entry:1") is True
        uow.audit.record(
            AuditEvent(
                event_type="ENTRY_STAGED",
                entity_id=str(ENTITY),
                actor_id="tester",
                occurred_at=NOW,
                payload={"entry_id": "entry:1"},
            )
        )
        uow.outbox.publish(
            OutboxRecord(
                event_type="ENTRY_STAGED",
                entity_id=str(ENTITY),
                payload={"entry_id": "entry:1"},
                idempotency_key="post:entry:1",
            )
        )
        uow.rollback()

    assert JournalModel.objects.count() == 0
    assert AccountingPeriodModel.objects.count() == 0
    assert JournalEntryModel.objects.count() == 0
    assert JournalLineModel.objects.count() == 0
    assert AuditEventModel.objects.count() == 0
    assert OutboxMessageModel.objects.count() == 0
    assert IdempotencyRecordModel.objects.count() == 0


def test_commit_persists_accounting_audit_outbox_and_idempotency_atomically() -> None:
    factory = DjangoUnitOfWorkFactory(clock=FrozenClock(NOW))

    with factory.open() as uow:
        uow.journals.add(_journal())
        uow.periods.add(_period())
        uow.entries.add(_entry())
        assert uow.idempotency.claim("post:entry:1") is True
        uow.idempotency.complete("post:entry:1")
        uow.audit.record(
            AuditEvent(
                event_type="ENTRY_STAGED",
                entity_id=str(ENTITY),
                actor_id="tester",
                occurred_at=NOW,
                payload={"entry_id": "entry:1"},
            )
        )
        uow.outbox.publish(
            OutboxRecord(
                event_type="ENTRY_STAGED",
                entity_id=str(ENTITY),
                payload={"entry_id": "entry:1"},
                idempotency_key="post:entry:1",
            )
        )
        uow.commit()

    assert JournalEntryModel.objects.get(pk="entry:1").revision == 0
    assert AuditEventModel.objects.values_list("event_type", flat=True).get() == "ENTRY_STAGED"
    assert OutboxMessageModel.objects.values_list("event_type", flat=True).get() == "ENTRY_STAGED"
    assert IdempotencyRecordModel.objects.get(pk="post:entry:1").status == "completed"
