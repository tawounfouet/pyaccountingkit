"""Hypothesis property tests for the double-entry balance invariants (gate GA)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import (
    DebitAndCreditSetError,
    EmptyEntryError,
    NegativeAmountError,
    UnbalancedEntryError,
    ZeroLineError,
)
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine

_positive_money_amounts = st.integers(min_value=1, max_value=10**8).map(Decimal)


def _positive_amounts(n: int) -> st.SearchStrategy[tuple[Decimal, ...]]:
    return st.tuples(*(_positive_money_amounts for _ in range(n)))


@given(_positive_money_amounts)
def test_large_balanced_entry_is_valid(total: Decimal) -> None:
    entry = JournalEntry(
        id=EntryId("e"),
        journal_id=JournalId("j"),
        period_id=PeriodId("p"),
        entry_date=date(2024, 1, 1),
        description="balanced",
        lines=(
            JournalLine(account_id="a", debit=Money(total, EUR), credit=Money.zero(EUR)),
            JournalLine(account_id="b", debit=Money.zero(EUR), credit=Money(total, EUR)),
        ),
    )
    assert entry.is_balanced()
    assert entry.total_debit() == entry.total_credit()


@given(_positive_amounts(4))
def test_multiline_entry_sums_exactly(amounts: tuple[Decimal, ...]) -> None:
    debit_a, debit_b, credit_a, credit_b = amounts
    lines = (
        JournalLine(account_id="a", debit=Money(debit_a, EUR), credit=Money.zero(EUR)),
        JournalLine(account_id="b", debit=Money(debit_b, EUR), credit=Money.zero(EUR)),
        JournalLine(account_id="c", debit=Money.zero(EUR), credit=Money(credit_a, EUR)),
        JournalLine(account_id="d", debit=Money.zero(EUR), credit=Money(credit_b, EUR)),
    )
    if debit_a + debit_b != credit_a + credit_b:
        with pytest.raises(UnbalancedEntryError):
            JournalEntry(
                id=EntryId("e"),
                journal_id=JournalId("j"),
                period_id=PeriodId("p"),
                entry_date=date(2024, 1, 1),
                description="unbalanced",
                lines=lines,
            )
    else:
        entry = JournalEntry(
            id=EntryId("e"),
            journal_id=JournalId("j"),
            period_id=PeriodId("p"),
            entry_date=date(2024, 1, 1),
            description="balanced",
            lines=lines,
        )
        assert entry.total_debit() == entry.total_credit()


@given(st.integers(min_value=1, max_value=10**8))
def test_debit_credit_mutual_exclusion(amount: int) -> None:
    with pytest.raises(DebitAndCreditSetError):
        JournalLine(
            account_id="a",
            debit=Money(Decimal(amount), EUR),
            credit=Money(Decimal(amount), EUR),
        )


@given(st.integers(min_value=1, max_value=10**8))
def test_negative_line_amounts_rejected(amount: int) -> None:
    with pytest.raises(NegativeAmountError):
        JournalLine(
            account_id="a",
            debit=Money(-Decimal(amount), EUR),
            credit=Money.zero(EUR),
        )


def test_zero_line_is_rejected_by_construction() -> None:
    with pytest.raises(ZeroLineError):
        JournalLine(
            account_id="a",
            debit=Money.zero(EUR),
            credit=Money.zero(EUR),
        )


@given(_positive_amounts(3))
def test_minimum_two_lines_invariant(amounts: tuple[Decimal, ...]) -> None:
    total = sum(amounts)
    too_small = (
        JournalLine(
            account_id="a",
            debit=Money(amounts[0], EUR),
            credit=Money.zero(EUR),
        ),
    )
    with pytest.raises(EmptyEntryError):
        JournalEntry(
            id=EntryId("e"),
            journal_id=JournalId("j"),
            period_id=PeriodId("p"),
            entry_date=date(2024, 1, 1),
            description="one line",
            lines=too_small,
        )
    assert total >= amounts[0]
