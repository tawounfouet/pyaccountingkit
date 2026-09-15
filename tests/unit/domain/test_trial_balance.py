"""Unit tests for the domain trial balance object (LOT-07)."""

from __future__ import annotations

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import UnbalancedEntryError
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.reporting.trial_balance import (
    TrialBalance,
    TrialBalanceSnapshot,
)


def _line(code: str, debit: str, credit: str) -> AccountBalanceLine:
    return AccountBalanceLine(
        account_code=code,
        label=f"Compte {code}",
        sum_debit=Money.from_str(debit, EUR),
        sum_credit=Money.from_str(credit, EUR),
    )


def test_balance_sign_convention() -> None:
    line = _line("411000", "250.50", "0.00")
    assert line.is_debit_balance
    assert not line.is_credit_balance
    credit_line = _line("707000", "0.00", "250.50")
    assert credit_line.is_credit_balance
    assert not credit_line.is_debit_balance
    assert line.balance == Money.from_str("250.50", EUR)
    assert credit_line.balance == -Money.from_str("250.50", EUR)


def test_build_sums_and_balances() -> None:
    tb = TrialBalance.build(
        "p_2024_01",
        TrialBalanceSnapshot.BEFORE_ADJUSTMENTS,
        (_line("411000", "100.00", "0.00"), _line("707000", "0.00", "100.00")),
    )
    assert tb.total_debit == Money.from_str("100.00", EUR)
    assert tb.total_credit == Money.from_str("100.00", EUR)
    assert [line.account_code for line in tb.lines] == ["411000", "707000"]
    assert tb.lines_for_account("411000").sum_debit == Money.from_str("100.00", EUR)


def test_build_rejects_unbalanced() -> None:
    with pytest.raises(UnbalancedEntryError):
        TrialBalance.build(
            "p_2024_01",
            TrialBalanceSnapshot.ADJUSTED,
            (_line("411000", "100.00", "0.00"), _line("707000", "0.00", "90.00")),
        )


def test_checksum_deterministic() -> None:
    lines = (_line("411000", "100.00", "0.00"), _line("707000", "0.00", "100.00"))
    first = TrialBalance.build("p_2024_01", TrialBalanceSnapshot.BEFORE_ADJUSTMENTS, lines)
    second = TrialBalance.build("p_2024_01", TrialBalanceSnapshot.BEFORE_ADJUSTMENTS, lines)
    assert first.checksum == second.checksum
    other = TrialBalance.build(
        "p_2024_01",
        TrialBalanceSnapshot.BEFORE_ADJUSTMENTS,
        (_line("411000", "1.00", "0.00"), _line("707000", "0.00", "1.00")),
    )
    assert first.checksum != other.checksum


def test_checksum_distinguishes_snapshots_and_periods() -> None:
    lines = (_line("411000", "100.00", "0.00"), _line("707000", "0.00", "100.00"))
    a = TrialBalance.build("p_2024_01", TrialBalanceSnapshot.BEFORE_ADJUSTMENTS, lines)
    b = TrialBalance.build("p_2024_02", TrialBalanceSnapshot.BEFORE_ADJUSTMENTS, lines)
    c = TrialBalance.build("p_2024_01", TrialBalanceSnapshot.ADJUSTED, lines)
    assert a.checksum != b.checksum
    assert a.checksum != c.checksum


def test_lines_sorted_by_code_case_insensitive_order() -> None:
    tb = TrialBalance.build(
        "p",
        TrialBalanceSnapshot.POST_CLOSING,
        (_line("707000", "0.00", "5.00"), _line("411000", "5.00", "0.00")),
    )
    assert tb.lines[0].account_code == "411000"
    assert tb.lines[1].account_code == "707000"
