"""Reusable repository/UnitOfWork contract tests.

These tests are written against the ports only and are reused by every
persistence adapter (in-memory reference today, SQLAlchemy/PostgreSQL and
Django adapters later).  Add a new factory to FACTORIES to extend coverage.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.adapters.in_memory.unit_of_work import InMemoryUnitOfWorkFactory
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import (
    EntryNotFoundError,
    IdempotencyConflictError,
    InvalidEntryStateError,
    PeriodNotFoundError,
    RevisionConflictError,
)
from pyaccountingkit.core.identifiers import (
    AccountId,
    EntityId,
    EntryId,
    FiscalYearId,
    JournalId,
    PeriodId,
)
from pyaccountingkit.core.money import Money
from pyaccountingkit.core.revisions import Revision
from pyaccountingkit.domain.journals.journal import Journal
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod
from pyaccountingkit.domain.periods.closing_status import ClosingStatus
from pyaccountingkit.domain.traceability.accounting_execution import AccountingExecutionTrace
from pyaccountingkit.ports.outbox import OutboxRecord
from pyaccountingkit.ports.unit_of_work import UnitOfWorkFactoryProtocol

FACTORIES: list[str] = ["in_memory"]


def _new_factory(name: str) -> UnitOfWorkFactoryProtocol:
    if name == "in_memory":
        return InMemoryUnitOfWorkFactory()
    raise AssertionError(f"Unknown repository factory: {name}")


def _balanced_entry(entry_id: EntryId | None = None) -> JournalEntry:
    return JournalEntry(
        id=entry_id or EntryId("entry_1"),
        journal_id=JournalId("j_ventes"),
        period_id=PeriodId("p_2024_01"),
        entry_date=date(2024, 1, 15),
        description="Vente TC",
        lines=(
            JournalLine(
                account_id="411000",
                debit=Money.from_str("100.00", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id="707000",
                debit=Money.zero(EUR),
                credit=Money.from_str("100.00", EUR),
            ),
        ),
    )


def _monthly_period() -> AccountingPeriod:
    return AccountingPeriod(
        id=PeriodId("p_2024_01"),
        entity_id=EntityId("ent_1"),
        fiscal_year_id=FiscalYearId("fy_2024"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
    )


def _execution_trace(entry_id: EntryId | None = None) -> AccountingExecutionTrace:
    resolved_entry_id = entry_id or EntryId("entry_1")
    return AccountingExecutionTrace(
        trace_id="acct:proposal-1",
        entity_id=EntityId("ent_1"),
        accounting_date=date(2024, 1, 15),
        proposal_checksum="a" * 64,
        resolved_account_ids=(AccountId("411000"), AccountId("707000")),
        journal_entry_id=resolved_entry_id,
        company_chart_id="chart:ent_1",
        company_chart_version="v1",
        company_chart_reference_snapshot_id="snapshot:1",
        policy_set_ids=("ps:1",),
        policy_set_versions=("1",),
        policy_ids=("policy:1",),
        policy_versions=("1.0",),
        policy_reference_snapshot_ids=("snapshot:1",),
        source_reference="source:1",
    )


def _sales_journal() -> Journal:
    return Journal(
        id=JournalId("j_ventes"),
        entity_id=EntityId("ent_1"),
        code="VENTES",
        label="Ventes",
    )


@pytest.fixture
def uow_factory() -> UnitOfWorkFactoryProtocol:
    return _new_factory("in_memory")


@pytest.mark.parametrize("name", FACTORIES)
def test_entry_add_and_get_roundtrip(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        entry = _balanced_entry()
        uow.entries.add(entry)
        assert uow.entries.get(entry.id) == entry
        uow.commit()


@pytest.mark.parametrize("name", FACTORIES)
def test_entry_add_twice_is_rejected(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        uow.entries.add(_balanced_entry())
        uow.commit()
    with factory.open() as uow:
        with pytest.raises(RevisionConflictError):
            uow.entries.add(_balanced_entry())
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_entry_get_missing_raises(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        with pytest.raises(EntryNotFoundError):
            uow.entries.get(EntryId("missing"))
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_save_with_stale_revision_conflicts(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        uow.entries.add(_balanced_entry())
        uow.commit()
    with factory.open() as uow:
        entry = uow.entries.get(EntryId("entry_1"))
        uow.entries.save(entry, Revision())
        uow.commit()
    with factory.open() as uow:
        posted = uow.entries.get(EntryId("entry_1"))
        with pytest.raises(RevisionConflictError):
            uow.entries.save(posted, Revision())
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_posted_entry_economics_are_immutable(name: str) -> None:
    factory = _new_factory(name)
    posted = _balanced_entry().validate().freeze(datetime(2024, 1, 15, 9, 0, tzinfo=UTC))

    with factory.open() as uow:
        uow.entries.add(posted)
        uow.commit()

    with factory.open() as uow:
        revision = uow.entries.get_revision(posted.id)
        with pytest.raises(InvalidEntryStateError, match="immutable"):
            uow.entries.save(replace(posted, description="rewritten"), revision)
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_commit_persists_period_and_journal(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        period = _monthly_period()
        journal = _sales_journal()
        uow.periods.add(period)
        uow.journals.add(journal)
        uow.commit()
    with factory.open() as uow:
        assert uow.periods.get(period.id) == period
        assert uow.journals.get(journal.id) == journal
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_uncommitted_transaction_is_discarded(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        uow.entries.add(_balanced_entry())
    with factory.open() as uow:
        with pytest.raises(EntryNotFoundError):
            uow.entries.get(EntryId("entry_1"))
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_idempotency_key_claimed_once(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        assert uow.idempotency.claim("post:entry_1")
        uow.idempotency.complete("post:entry_1")
        uow.commit()
    with factory.open() as uow:
        assert not uow.idempotency.claim("post:entry_1")
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_idempotency_same_key_different_payload_conflicts(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        assert uow.idempotency.claim("post:entry_1", "fingerprint-a")
        uow.idempotency.complete("post:entry_1")
        uow.commit()

    with factory.open() as uow:
        with pytest.raises(IdempotencyConflictError):
            uow.idempotency.claim("post:entry_1", "fingerprint-b")
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_period_save_missing_raises(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        with pytest.raises(PeriodNotFoundError):
            uow.periods.save(_monthly_period())
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_period_save_rejects_immutable_field_rewrite(name: str) -> None:
    factory = _new_factory(name)
    period = _monthly_period()
    with factory.open() as uow:
        uow.periods.add(period)
        uow.commit()

    with factory.open() as uow:
        with pytest.raises(ValueError, match="immutable"):
            uow.periods.save(replace(period, end_date=date(2024, 2, 1)))
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_period_save_rejects_skipped_transition(name: str) -> None:
    factory = _new_factory(name)
    period = _monthly_period()
    with factory.open() as uow:
        uow.periods.add(period)
        uow.commit()

    with factory.open() as uow:
        with pytest.raises(ValueError, match="Transition persistante invalide"):
            uow.periods.save(replace(period, status=ClosingStatus.CLOSED))
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_period_save_accepts_legal_transition(name: str) -> None:
    factory = _new_factory(name)
    period = _monthly_period()
    with factory.open() as uow:
        uow.periods.add(period)
        uow.commit()

    reviewed = period.with_status(ClosingStatus.REVIEW)
    with factory.open() as uow:
        uow.periods.save(reviewed)
        uow.commit()

    with factory.open() as uow:
        assert uow.periods.get(period.id) == reviewed
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_execution_trace_commits_with_entry(name: str) -> None:
    factory = _new_factory(name)
    entry = _balanced_entry()
    trace = _execution_trace(entry.id)

    with factory.open() as uow:
        uow.entries.add(entry)
        uow.execution_traces.append(trace)
        uow.commit()

    with factory.open() as uow:
        assert uow.entries.get(entry.id) == entry
        assert uow.execution_traces.get_by_entry_id(entry.id) == trace
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_execution_trace_rolls_back_with_entry(name: str) -> None:
    factory = _new_factory(name)
    entry = _balanced_entry()
    trace = _execution_trace(entry.id)

    with factory.open() as uow:
        uow.entries.add(entry)
        uow.execution_traces.append(trace)
        uow.rollback()

    with factory.open() as uow:
        with pytest.raises(EntryNotFoundError):
            uow.entries.get(entry.id)
        assert uow.execution_traces.get_by_entry_id(entry.id) is None
        uow.rollback()


@pytest.mark.parametrize("name", FACTORIES)
def test_outbox_message_buffered_until_commit(name: str) -> None:
    factory = _new_factory(name)
    with factory.open() as uow:
        uow.outbox.publish(OutboxRecord(event_type="ENTRY_QUEUED", entity_id="entry_1"))
        uow.commit()
