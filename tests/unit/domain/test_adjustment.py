"""Unit tests for adjustment proposals (LOT-09)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import EntryNotPostedError
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.closing.adjustment import AdjustmentProposal
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine

NOW = datetime(2024, 12, 31, 10, 0, tzinfo=UTC)


def _posted() -> JournalEntry:
    return JournalEntry(
        id=EntryId("e_src"),
        journal_id=JournalId("j"),
        period_id=PeriodId("p"),
        entry_date=date(2024, 12, 15),
        description="source",
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
        status=EntryStatus.POSTED,
        posted_at=NOW,
    )


def _adjustment() -> JournalEntry:
    return JournalEntry(
        id=EntryId("e_adj"),
        journal_id=JournalId("j"),
        period_id=PeriodId("p"),
        entry_date=date(2024, 12, 20),
        description="ajustement",
        lines=_posted().lines,
        status=EntryStatus.VALIDATED,
    )


def test_proposal_requires_posted_source() -> None:
    draft = JournalEntry(
        id=EntryId("e_draft"),
        journal_id=JournalId("j"),
        period_id=PeriodId("p"),
        entry_date=date(2024, 12, 15),
        description="draft",
        lines=_posted().lines,
        status=EntryStatus.DRAFT,
    )
    with pytest.raises(EntryNotPostedError):
        AdjustmentProposal(id="ap1", source_entry=draft, adjustment=_adjustment(), proposed_at=NOW)
    AdjustmentProposal(id="ap1", source_entry=_posted(), adjustment=_adjustment(), proposed_at=NOW)


def test_adjustment_never_mutates_posted_source() -> None:
    proposal = AdjustmentProposal(
        id="ap1",
        source_entry=_posted(),
        adjustment=_adjustment(),
        proposed_at=NOW,
    )
    original = _posted()
    proposal.applies()
    assert proposal.source_entry == original
    assert proposal.source_entry.posted_at == NOW
    assert proposal.adjustment.id == EntryId("e_adj")
    assert proposal.adjustment.reversal_of_id is None
