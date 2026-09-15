"""Unit tests for the JournalEntry aggregate root and line invariants."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import EmptyEntryError, UnbalancedEntryError, ZeroLineError
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine


def _line(debit: str = "0", credit: str = "0", account: str = "411") -> JournalLine:
    return JournalLine(
        account_id=account,
        debit=Money.from_str(debit, EUR),
        credit=Money.from_str(credit, EUR),
    )


def _balanced_entry() -> JournalEntry:
    return JournalEntry(
        id=EntryId("ent_1"),
        journal_id=JournalId("j_vente"),
        period_id=PeriodId("p_2024"),
        entry_date=date(2024, 1, 15),
        description="Vente marchandise",
        lines=(
            _line(debit="100.00", account="411"),
            _line(credit="100.00", account="707"),
        ),
    )


def test_valid_entry_is_draft() -> None:
    entry = _balanced_entry()
    assert entry.status is EntryStatus.DRAFT
    assert entry.is_balanced()


def test_journal_line_rejects_zero_zero_at_construction() -> None:
    with pytest.raises(ZeroLineError):
        _line()


def test_entry_requires_at_least_two_lines() -> None:
    with pytest.raises(EmptyEntryError):
        JournalEntry(
            id=EntryId("e"),
            journal_id=JournalId("j"),
            period_id=PeriodId("p"),
            entry_date=date(2024, 1, 1),
            description="une ligne",
            lines=(_line(debit="100.00"),),
        )


def test_entry_rejects_empty_lines() -> None:
    with pytest.raises(EmptyEntryError):
        JournalEntry(
            id=EntryId("e"),
            journal_id=JournalId("j"),
            period_id=PeriodId("p"),
            entry_date=date(2024, 1, 1),
            description="vide",
            lines=(),
        )


def test_entry_rejects_unbalanced_debit_credit() -> None:
    with pytest.raises(UnbalancedEntryError):
        JournalEntry(
            id=EntryId("e"),
            journal_id=JournalId("j"),
            period_id=PeriodId("p"),
            entry_date=date(2024, 1, 1),
            description="déséquilibrée",
            lines=(
                _line(debit="100.00"),
                _line(credit="90.00"),
            ),
        )


def test_entry_total_debit_credit_exact() -> None:
    entry = _balanced_entry()
    assert entry.total_debit() == Money.from_str("100.00", EUR)
    assert entry.total_credit() == Money.from_str("100.00", EUR)


def test_entry_is_immutable() -> None:
    entry = _balanced_entry()
    with pytest.raises(AttributeError):
        entry.status = EntryStatus.POSTED  # type: ignore[misc]


def test_entry_defaults_optional_fields() -> None:
    entry = _balanced_entry()
    assert entry.posted_at is None
    assert entry.reversal_of_id is None
    assert entry.reversed_by_id is None


def test_entry_accepts_validated_status() -> None:
    entry = JournalEntry(
        id=EntryId("e"),
        journal_id=JournalId("j"),
        period_id=PeriodId("p"),
        entry_date=date(2024, 1, 1),
        description="validée",
        lines=(
            _line(debit="50.00"),
            _line(credit="50.00"),
        ),
        status=EntryStatus.VALIDATED,
    )
    assert entry.status is EntryStatus.VALIDATED
