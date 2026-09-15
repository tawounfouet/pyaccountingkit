"""Unit tests for the pure domain reversal service."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import (
    AlreadyReversedError,
    EntryNotPostedError,
    InvalidReversalDateError,
)
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.audit.events import AuditEvent
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.ledger.reversal import create_reversal
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod

NOW = datetime(2024, 2, 10, 9, 0, tzinfo=UTC)


class RecordingAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


def _posted() -> JournalEntry:
    return JournalEntry(
        id=EntryId("e1"),
        journal_id=JournalId("j"),
        period_id=PeriodId("p_2024_01"),
        entry_date=date(2024, 1, 15),
        description="Vente TC",
        status=EntryStatus.POSTED,
        posted_at=datetime(2024, 1, 15, 8, 0, tzinfo=UTC),
        lines=(
            JournalLine(
                account_id="411",
                debit=Money.from_str("100.00", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(
                account_id="707",
                debit=Money.zero(EUR),
                credit=Money.from_str("100.00", EUR),
            ),
        ),
    )


def _target_period() -> AccountingPeriod:
    from pyaccountingkit.core.identifiers import EntityId, FiscalYearId

    return AccountingPeriod(
        id=PeriodId("p_2024_02"),
        entity_id=EntityId("ent"),
        fiscal_year_id=FiscalYearId("fy"),
        start_date=date(2024, 2, 1),
        end_date=date(2024, 2, 29),
    )


def _sink() -> tuple[RecordingAuditSink, FrozenClock]:
    return RecordingAuditSink(), FrozenClock(NOW)


def _do_reverse() -> tuple[JournalEntry, JournalEntry, RecordingAuditSink]:
    sink, clock = _sink()
    marked, reversal = create_reversal(
        original=_posted(),
        reversal_date=date(2024, 2, 10),
        reversal_id=EntryId("rev_1"),
        target_period=_target_period(),
        audit_sink=sink,
        clock=clock,
        user_id="u1",
    )
    return marked, reversal, sink


def test_reversal_creates_new_inverse_entry() -> None:
    marked, reversal, _ = _do_reverse()
    assert reversal.id == EntryId("rev_1")
    assert reversal.status is EntryStatus.POSTED
    assert reversal.entry_date == date(2024, 2, 10)
    assert reversal.reversal_of_id == EntryId("e1")
    assert reversal.description == "Contrepassation de e1"


def test_reversal_inverts_debit_and_credit() -> None:
    marked, reversal, _ = _do_reverse()
    assert reversal.lines[0].credit == Money.from_str("100.00", EUR)
    assert reversal.lines[0].debit == Money.zero(EUR)
    assert reversal.lines[1].debit == Money.from_str("100.00", EUR)
    assert reversal.lines[1].credit == Money.zero(EUR)
    assert reversal.is_balanced()


def test_marked_original_keeps_accounting_lines() -> None:
    marked, _, _ = _do_reverse()
    assert marked.status is EntryStatus.POSTED
    assert marked.id == EntryId("e1")
    assert marked.reversed_by_id == EntryId("rev_1")
    assert marked.lines == _posted().lines
    assert marked.is_balanced()


def test_reversal_records_audit_event() -> None:
    _, _, sink = _do_reverse()
    assert len(sink.events) == 1
    assert sink.events[0].event_type == "ENTRY_REVERSED"
    assert sink.events[0].actor_id == "u1"


def test_reversal_rejects_non_posted_entry() -> None:
    draft = JournalEntry(
        id=EntryId("e2"),
        journal_id=JournalId("j"),
        period_id=PeriodId("p_2024_01"),
        entry_date=date(2024, 1, 15),
        description="brouillon",
        lines=(_posted().lines),
    )
    assert draft.status is EntryStatus.DRAFT
    sink, clock = _sink()
    with pytest.raises(EntryNotPostedError):
        create_reversal(
            original=draft,
            reversal_date=date(2024, 2, 10),
            reversal_id=EntryId("rev_2"),
            target_period=_target_period(),
            audit_sink=sink,
            clock=clock,
            user_id="u1",
        )


def test_reversal_rejects_already_reversed_entry() -> None:
    already = JournalEntry(
        id=EntryId("e3"),
        journal_id=JournalId("j"),
        period_id=PeriodId("p_2024_01"),
        entry_date=date(2024, 1, 15),
        description="deja",
        status=EntryStatus.POSTED,
        posted_at=datetime(2024, 1, 15, 8, 0, tzinfo=UTC),
        reversed_by_id=EntryId("rev_old"),
        lines=(_posted().lines),
    )
    sink, clock = _sink()
    with pytest.raises(AlreadyReversedError):
        create_reversal(
            original=already,
            reversal_date=date(2024, 2, 10),
            reversal_id=EntryId("rev_3"),
            target_period=_target_period(),
            audit_sink=sink,
            clock=clock,
            user_id="u1",
        )


def test_reversal_rejects_date_outside_target_period() -> None:
    sink, clock = _sink()
    with pytest.raises(InvalidReversalDateError):
        create_reversal(
            original=_posted(),
            reversal_date=date(2024, 3, 1),
            reversal_id=EntryId("rev_4"),
            target_period=_target_period(),
            audit_sink=sink,
            clock=clock,
            user_id="u1",
        )
