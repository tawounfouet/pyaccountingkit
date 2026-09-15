"""Unit tests for the pure domain PostingService (PLAN-01 §3.3)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import (
    EntryAlreadyPostedError,
    PeriodClosedError,
    UnbalancedEntryError,
)
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.ledger.posting import PostingService
from pyaccountingkit.domain.periods.accounting_period import AccountingPeriod

NOW = datetime(2024, 3, 15, 10, 0, tzinfo=UTC)


def _period(*, closed: bool = False) -> AccountingPeriod:
    from pyaccountingkit.core.identifiers import EntityId, FiscalYearId
    from pyaccountingkit.domain.periods.closing_status import ClosingStatus

    status = ClosingStatus.CLOSED if closed else ClosingStatus.OPEN
    return AccountingPeriod(
        id=PeriodId("p_2024_01"),
        entity_id=EntityId("ent"),
        fiscal_year_id=FiscalYearId("fy"),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        status=status,
    )


def _draft(*, balanced: bool = True, status: EntryStatus = EntryStatus.DRAFT) -> JournalEntry:
    credit = Money.from_str("100.00", EUR) if balanced else Money.from_str("90.00", EUR)
    return JournalEntry(
        id=EntryId("e1"),
        journal_id=JournalId("j"),
        period_id=PeriodId("p_2024_01"),
        entry_date=date(2024, 1, 15),
        description="test",
        status=status,
        lines=(
            JournalLine(
                account_id="411",
                debit=Money.from_str("100.00", EUR),
                credit=Money.zero(EUR),
            ),
            JournalLine(account_id="707", debit=Money.zero(EUR), credit=credit),
        ),
    )


def _service() -> PostingService:
    return PostingService(clock=FrozenClock(NOW))


def test_posting_produces_a_posted_copy() -> None:
    posted = _service().post(_draft(), _period(), user_id="u1")
    assert posted.status is EntryStatus.POSTED
    assert posted.posted_at == NOW


def test_posting_rejects_already_posted() -> None:
    with pytest.raises(EntryAlreadyPostedError):
        _service().post(_draft(status=EntryStatus.POSTED), _period(), user_id="u1")


def test_posting_rejects_reversed() -> None:
    with pytest.raises(EntryAlreadyPostedError):
        _service().post(_draft(status=EntryStatus.REVERSED), _period(), user_id="u1")


def test_posting_rejects_unbalanced_entry() -> None:
    with pytest.raises(UnbalancedEntryError):
        _service().post(_draft(balanced=False), _period(), user_id="u1")


def test_posting_rejects_closed_period() -> None:
    with pytest.raises(PeriodClosedError):
        _service().post(_draft(), _period(closed=True), user_id="u1")


def test_posting_preserves_reversal_and_reversed_by() -> None:
    posted = _service().post(_draft(), _period(), user_id="u1")
    assert posted.reversal_of_id is None
    assert posted.reversed_by_id is None
