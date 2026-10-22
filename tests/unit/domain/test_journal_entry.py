"""Unit tests for the JournalEntry aggregate root and line invariants."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import (
    EmptyEntryError,
    InvalidEntryStateError,
    UnbalancedEntryError,
    ZeroLineError,
)
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, EntryType, JournalEntry
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


def test_valid_entry_is_draft_normal_and_balanced() -> None:
    entry = _balanced_entry()
    assert entry.status is EntryStatus.DRAFT
    assert entry.entry_type is EntryType.NORMAL
    assert entry.is_balanced()


def test_validate_returns_immutable_validated_copy_and_preserves_type() -> None:
    entry = JournalEntry(
        id=EntryId("opening"),
        journal_id=JournalId("j_vente"),
        period_id=PeriodId("p_2024"),
        entry_date=date(2024, 1, 1),
        description="opening",
        lines=(
            _line(debit="100.00", account="512"),
            _line(credit="100.00", account="101"),
        ),
        entry_type=EntryType.OPENING,
    )
    validated = entry.validate()
    assert entry.status is EntryStatus.DRAFT
    assert validated.status is EntryStatus.VALIDATED
    assert validated.entry_type is EntryType.OPENING


def test_validate_rejects_non_draft_entry() -> None:
    validated = _balanced_entry().validate()
    with pytest.raises(InvalidEntryStateError):
        validated.validate()


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


def test_posted_entry_rejects_persistence_successor_with_changed_economics() -> None:
    posted = _balanced_entry().validate().freeze(datetime(2024, 1, 15, 9, 0, tzinfo=UTC))
    changed = JournalEntry(
        id=posted.id,
        journal_id=posted.journal_id,
        period_id=posted.period_id,
        entry_date=posted.entry_date,
        description="changed after posting",
        lines=posted.lines,
        entry_type=posted.entry_type,
        status=EntryStatus.POSTED,
        posted_at=posted.posted_at,
        reversal_of_id=posted.reversal_of_id,
        reversed_by_id=posted.reversed_by_id,
    )

    with pytest.raises(InvalidEntryStateError, match="immutable"):
        posted.assert_persistence_successor(changed)


def test_posted_entry_allows_reversed_persistence_successor_without_economic_change() -> None:
    posted = _balanced_entry().validate().freeze(datetime(2024, 1, 15, 9, 0, tzinfo=UTC))
    reversed_entry = JournalEntry(
        id=posted.id,
        journal_id=posted.journal_id,
        period_id=posted.period_id,
        entry_date=posted.entry_date,
        description=posted.description,
        lines=posted.lines,
        entry_type=posted.entry_type,
        status=EntryStatus.REVERSED,
        posted_at=posted.posted_at,
        reversal_of_id=posted.reversal_of_id,
        reversed_by_id=EntryId("rev:1"),
    )

    posted.assert_persistence_successor(reversed_entry)


def test_reversed_entry_rejects_further_persistence_mutation() -> None:
    posted = _balanced_entry().validate().freeze(datetime(2024, 1, 15, 9, 0, tzinfo=UTC))
    reversed_entry = JournalEntry(
        id=posted.id,
        journal_id=posted.journal_id,
        period_id=posted.period_id,
        entry_date=posted.entry_date,
        description=posted.description,
        lines=posted.lines,
        entry_type=posted.entry_type,
        status=EntryStatus.REVERSED,
        posted_at=posted.posted_at,
        reversed_by_id=EntryId("rev:1"),
    )
    mutated = JournalEntry(
        id=reversed_entry.id,
        journal_id=reversed_entry.journal_id,
        period_id=reversed_entry.period_id,
        entry_date=reversed_entry.entry_date,
        description=reversed_entry.description,
        lines=reversed_entry.lines,
        entry_type=reversed_entry.entry_type,
        status=EntryStatus.REVERSED,
        posted_at=reversed_entry.posted_at,
        reversed_by_id=EntryId("rev:2"),
    )

    with pytest.raises(InvalidEntryStateError, match="REVERSED"):
        reversed_entry.assert_persistence_successor(mutated)
