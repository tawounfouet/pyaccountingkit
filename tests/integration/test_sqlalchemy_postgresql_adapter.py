"""Real PostgreSQL qualification for the optional SQLAlchemy adapter."""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

if os.getenv("PYAK_SQLALCHEMY_POSTGRES_TEST") != "1":
    pytest.skip("SQLAlchemy/PostgreSQL qualification is disabled", allow_module_level=True)

from pyaccountingkit.adapters.sqlalchemy.tables import (
    AccountingExecutionTraceTable,
    AccountingPeriodTable,
    AuditEventTable,
    IdempotencyRecordTable,
    JournalEntryTable,
    JournalLineTable,
    JournalTable,
    OutboxMessageTable,
)
from pyaccountingkit.adapters.sqlalchemy.unit_of_work import SQLAlchemyUnitOfWorkFactory
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
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import EntryType, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus
from pyaccountingkit.domain.traceability.accounting_execution import AccountingExecutionTrace
from pyaccountingkit.ports.outbox import OutboxRecord

NOW = datetime(2026, 9, 19, 15, 0, tzinfo=UTC)
ENTITY = EntityId("entity:sqlalchemy")
JOURNAL_ID = JournalId("journal:sales")
PERIOD_ID = PeriodId("period:2026-09")
DATABASE_URL = os.environ["PYAK_SQLALCHEMY_DATABASE_URL"]
ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)


def _truncate(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE "
                "pyak_accounting_execution_trace, pyak_journal_line, "
                "pyak_journal_entry, pyak_outbox, "
                "pyak_audit_event, pyak_idempotency, pyak_accounting_period, "
                "pyak_journal RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture(autouse=True)
def clean_postgresql_adapter_tables() -> None:
    """Keep every SQLAlchemy qualification scenario isolated."""

    _truncate(ENGINE)


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
        accounting_date=date(2026, 9, 19),
        proposal_checksum="a" * 64,
        resolved_account_ids=(AccountId("411000"), AccountId("707000")),
        journal_entry_id=EntryId(entry_id),
        company_chart_id="chart:sqlalchemy",
        company_chart_version="v1",
        company_chart_reference_snapshot_id="snapshot:1",
        policy_set_ids=("ps:1",),
        policy_set_versions=("1",),
        policy_ids=("policy:1",),
        policy_versions=("1.0",),
        policy_reference_snapshot_ids=("snapshot:1",),
        source_reference="source:1",
    )


def _entry(entry_id: str = "entry:1") -> JournalEntry:
    return JournalEntry(
        id=EntryId(entry_id),
        journal_id=JOURNAL_ID,
        period_id=PERIOD_ID,
        entry_date=date(2026, 9, 19),
        description="SQLAlchemy/PostgreSQL adapter round-trip",
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
    factory = SQLAlchemyUnitOfWorkFactory(ENGINE, clock=FrozenClock(NOW))
    journal = _journal()
    period = _period()
    entry = _entry()

    with factory.open() as uow:
        uow.journals.add(journal)
        uow.periods.add(period)
        uow.entries.add(entry)
        uow.commit()

    with factory.open() as read:
        assert read.journals.get(JOURNAL_ID) == journal
        assert read.periods.get(PERIOD_ID) == period
        assert read.entries.get(EntryId("entry:1")) == entry
        read.rollback()

    with Session(ENGINE) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(JournalLineTable)
                .where(JournalLineTable.entry_id == "entry:1")
            )
            == 2
        )
        assert session.get(JournalEntryTable, "entry:1").entry_type == "ADJUSTING"


def test_posted_entry_economics_cannot_be_rewritten() -> None:
    factory = SQLAlchemyUnitOfWorkFactory(ENGINE, clock=FrozenClock(NOW))
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

    with factory.open() as read:
        assert read.entries.get(posted.id) == posted
        read.rollback()


def test_idempotency_key_rejects_different_payload_fingerprint() -> None:
    factory = SQLAlchemyUnitOfWorkFactory(ENGINE, clock=FrozenClock(NOW))
    with factory.open() as uow:
        assert uow.idempotency.claim("post:semantic", "fingerprint-a") is True
        uow.idempotency.complete("post:semantic")
        uow.commit()

    with factory.open() as uow:
        with pytest.raises(IdempotencyConflictError):
            uow.idempotency.claim("post:semantic", "fingerprint-b")
        uow.rollback()


def test_period_repository_rejects_skipped_transition_and_scope_rewrite() -> None:
    factory = SQLAlchemyUnitOfWorkFactory(ENGINE, clock=FrozenClock(NOW))
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
    factory = SQLAlchemyUnitOfWorkFactory(ENGINE, clock=FrozenClock(NOW))
    trace = _execution_trace()

    with factory.open() as uow:
        uow.journals.add(_journal())
        uow.periods.add(_period())
        uow.entries.add(_entry())
        uow.execution_traces.append(trace)
        uow.commit()

    with Session(ENGINE) as session:
        assert session.get(AccountingExecutionTraceTable, trace.trace_id) is not None

    with factory.open() as uow:
        assert uow.execution_traces.get_by_entry_id(EntryId("entry:1")) == trace
        uow.rollback()

    rolled_back_trace = _execution_trace("entry:rollback")
    with factory.open() as uow:
        uow.entries.add(_entry("entry:rollback"))
        uow.execution_traces.append(rolled_back_trace)
        uow.rollback()

    with Session(ENGINE) as session:
        assert session.get(JournalEntryTable, "entry:rollback") is None
        assert (
            session.get(
                AccountingExecutionTraceTable,
                rolled_back_trace.trace_id,
            )
            is None
        )


def test_uncommitted_unit_of_work_rolls_back_every_sink() -> None:
    factory = SQLAlchemyUnitOfWorkFactory(ENGINE, clock=FrozenClock(NOW))

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

    with Session(ENGINE) as session:
        for table in (
            JournalLineTable,
            JournalEntryTable,
            OutboxMessageTable,
            AuditEventTable,
            IdempotencyRecordTable,
            AccountingPeriodTable,
            JournalTable,
        ):
            assert session.scalar(select(func.count()).select_from(table)) == 0


def test_commit_persists_accounting_audit_outbox_and_idempotency_atomically() -> None:
    factory = SQLAlchemyUnitOfWorkFactory(ENGINE, clock=FrozenClock(NOW))

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

    with Session(ENGINE) as session:
        assert session.get(JournalEntryTable, "entry:1").revision == 0
        assert session.scalar(select(AuditEventTable.event_type)) == "ENTRY_STAGED"
        assert session.scalar(select(OutboxMessageTable.event_type)) == "ENTRY_STAGED"
        assert session.get(IdempotencyRecordTable, "post:entry:1").status == "completed"
