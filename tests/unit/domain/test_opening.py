"""Unit tests for opening balances generation (LOT-09)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import UnbalancedEntryError
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.closing.opening import (
    OpeningBalance,
    OpeningEntryBuilder,
    build_opening_balances,
)
from pyaccountingkit.domain.journals.journal_entry import EntryStatus
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine


def _line(code: str, debit: str, credit: str) -> AccountBalanceLine:
    return AccountBalanceLine(
        account_code=code,
        label=code,
        sum_debit=Money.from_str(debit, EUR),
        sum_credit=Money.from_str(credit, EUR),
    )


def test_build_opening_balances_keeps_signed_non_zero() -> None:
    lines = (
        _line("411000", "250.00", "0.00"),
        _line("707000", "0.00", "250.00"),
        _line("000000", "0.00", "0.00"),
    )
    openings = build_opening_balances(lines)
    assert openings == (
        OpeningBalance("411000", Money.from_str("250.00", EUR)),
        OpeningBalance("707000", Money.from_str("-250.00", EUR)),
    )


def test_opening_entry_is_balanced_and_posted() -> None:
    builder = OpeningEntryBuilder(opening_date=date(2025, 1, 1), evidence_run_id="c1")
    entry = builder.build(
        opening_balances=(
            OpeningBalance("411000", Money.from_str("250.00", EUR)),
            OpeningBalance("707000", Money.from_str("-250.00", EUR)),
        ),
        journal_id=JournalId("j_ouvert"),
        period_id=PeriodId("p_2025_01"),
        entry_id=EntryId("o1"),
    )
    assert entry.status is EntryStatus.POSTED
    assert entry.is_balanced()
    assert "Ouverture depuis clôture c1" in entry.description


def test_unbalanced_opening_rejected() -> None:
    builder = OpeningEntryBuilder(opening_date=date(2025, 1, 1), evidence_run_id="c1")
    with pytest.raises(UnbalancedEntryError):
        builder.build(
            opening_balances=(OpeningBalance("411000", Money.from_str("250.00", EUR)),),
            journal_id=JournalId("j_ouvert"),
            period_id=PeriodId("p_2025_01"),
            entry_id=EntryId("o1"),
        )


def test_empty_opening_rejected() -> None:
    builder = OpeningEntryBuilder(opening_date=date(2025, 1, 1), evidence_run_id="c1")
    with pytest.raises(UnbalancedEntryError):
        builder.build(
            opening_balances=(),
            journal_id=JournalId("j_ouvert"),
            period_id=PeriodId("p_2025_01"),
            entry_id=EntryId("o1"),
        )
