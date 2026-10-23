"""Real PostgreSQL qualification for the optional Django adapter."""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

if os.getenv("PYAK_POSTGRES_TEST") != "1":
    pytest.skip("PostgreSQL adapter qualification is disabled", allow_module_level=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.support.django_settings")

import django

django.setup()

from pyaccountingkit.adapters.django.models import (
    AccountingExecutionTraceModel,
    AccountingPeriodModel,
    AuditEventModel,
    ClosingRunModel,
    IdempotencyRecordModel,
    JournalEntryModel,
    JournalLineModel,
    JournalModel,
    OutboxMessageModel,
)
from pyaccountingkit.adapters.django.unit_of_work import DjangoUnitOfWorkFactory
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import IdempotencyConflictError, InvalidEntryStateError
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
from pyaccountingkit.domain.closing.closing_run import (
    ClosingEvidenceBundle,
    ClosingPhase,
    ClosingRun,
)
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryType, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus
from pyaccountingkit.domain.traceability.accounting_execution import AccountingExecutionTrace
from pyaccountingkit.ports.outbox import OutboxRecord

NOW = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)
ENTITY = EntityId("entity:postgres")
JOURNAL_ID = JournalId("journal:sales")
PERIOD_ID = PeriodId("period:2026-09")


@pytest.fixture(autouse=True)
def clean_postgresql_adapter_tables() -> None:
    """Keep every test isolated while exercising the real migrated schema."""

    ClosingRunModel.objects.all().delete()
    AccountingExecutionTraceModel.objects.all().delete()
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


def _execution_trace(entry_id: str = "entry:1") -> AccountingExecutionTrace:
    return AccountingExecutionTrace(
        trace_id=f"acct:{entry_id}",
        entity_id=ENTITY,
        accounting_date=date(2026, 9, 18),
        proposal_checksum="a" * 64,
        resolved_account_ids=(AccountId("411000"), AccountId("707000")),
        journal_entry_id=EntryId(entry_id),
        company_chart_id="chart:postgres",
        company_chart_version="v1",
        company_chart_reference_snapshot_id="snapshot:1",
        policy_set_ids=("ps:1",),
        policy_set_versions=("1",),
        policy_ids=("policy:1",),
        policy_versions=("1.0",),
        policy_reference_snapshot_ids=("snapshot:1",),
        source_reference="source:1",
    )


def _closing_run(run_id: str = "close:1") -> ClosingRun:
    evidence = ClosingEvidenceBundle(
        run_id=run_id,
        period_id=str(PERIOD_ID),
        trial_balance_checksum="b" * 64,
        control_runs_hash="c" * 64,
        total_debit="125.50",
        total_credit="125.50",
        sealed_at=NOW,
    )
    return ClosingRun(
        id=run_id,
        period_id=str(PERIOD_ID),
        phase=ClosingPhase.SEALED,
        evidence=evidence,
    )


def _entry(entry_id: str = "entry:1") -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JOURNAL_ID,
        period_id=PERIOD_ID,
        entry_date=date(2026, 9, 18),
        description="PostgreSQL adapter round-trip",
        entry_type=EntryType.ADJUSTING,
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
    assert JournalEntryModel.objects.get(pk="entry:1").entry_type == "ADJUSTING"


def test_posted_entry_economics_cannot_be_rewritten() -> None:
    factory = DjangoUnitOfWorkFactory(clock=FrozenClock(NOW))
    posted = _entry().validate().freeze(NOW)

    with factory.open() as uow:
        uow.journals.add(_journal())
        uow.periods.add(_period())
        uow.entries.add(posted)
        uow.commit()

    with factory.open() as uow:
        revision = uow.entries.get_revision(posted.id)
        with pytest.raises(InvalidEntryStateError, match="immutable"):
            uow.entries.save(replace(posted, description="rewritten"), revision)
        uow.rollback()

    assert DjangoUnitOfWorkFactory(clock=FrozenClock(NOW)).open().entries.get(posted.id) == posted


def test_idempotency_key_rejects_different_payload_fingerprint() -> None:
    factory = DjangoUnitOfWorkFactory(clock=FrozenClock(NOW))
    with factory.open() as uow:
        assert uow.idempotency.claim("post:semantic", "fingerprint-a") is True
        uow.idempotency.complete("post:semantic")
        uow.commit()

    with factory.open() as uow:
        with pytest.raises(IdempotencyConflictError):
            uow.idempotency.claim("post:semantic", "fingerprint-b")
        uow.rollback()


def test_period_repository_rejects_skipped_transition_and_scope_rewrite() -> None:
    factory = DjangoUnitOfWorkFactory(clock=FrozenClock(NOW))
    period = _period()
    with factory.open() as uow:
        uow.periods.add(period)
        uow.commit()

    with factory.open() as uow:
        with pytest.raises(ValueError, match="Transition persistante invalide"):
            uow.periods.save(replace(period, status=ClosingStatus.CLOSED))
        uow.rollback()

    with factory.open() as uow:
        with pytest.raises(ValueError, match="immutable"):
            uow.periods.save(replace(period, entity_id=EntityId("entity:other")))
        uow.rollback()


def test_execution_trace_is_atomic_with_accounting_entry() -> None:
    factory = DjangoUnitOfWorkFactory(clock=FrozenClock(NOW))
    trace = _execution_trace()

    with factory.open() as uow:
        uow.journals.add(_journal())
        uow.periods.add(_period())
        uow.entries.add(_entry())
        uow.execution_traces.append(trace)
        uow.commit()

    assert AccountingExecutionTraceModel.objects.filter(pk=trace.trace_id).count() == 1
    with factory.open() as uow:
        assert uow.execution_traces.get_by_entry_id(EntryId("entry:1")) == trace
        uow.rollback()

    rolled_back_trace = _execution_trace("entry:rollback")
    with factory.open() as uow:
        uow.entries.add(_entry("entry:rollback"))
        uow.execution_traces.append(rolled_back_trace)
        uow.rollback()

    assert not JournalEntryModel.objects.filter(pk="entry:rollback").exists()
    assert not AccountingExecutionTraceModel.objects.filter(pk=rolled_back_trace.trace_id).exists()


def test_closing_run_is_durable_and_atomic_in_django_uow() -> None:
    factory = DjangoUnitOfWorkFactory(clock=FrozenClock(NOW))
    run = _closing_run()

    with factory.open() as uow:
        uow.periods.add(_period())
        uow.closing_runs.append(run)
        uow.commit()

    assert ClosingRunModel.objects.filter(pk=run.id).count() == 1
    with factory.open() as read:
        assert read.closing_runs.get(run.id) == run
        read.rollback()

    rolled_back = _closing_run("close:rollback")
    with factory.open() as uow:
        uow.closing_runs.append(rolled_back)
        uow.rollback()

    assert not ClosingRunModel.objects.filter(pk=rolled_back.id).exists()


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
