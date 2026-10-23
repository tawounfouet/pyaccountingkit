"""Unit tests for opening balances generation (LOT-09)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import UnbalancedEntryError
from pyaccountingkit.core.identifiers import AccountId, EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.closing.opening import (
    OpeningBalance,
    OpeningBalanceIdentityError,
    OpeningEntryBuilder,
    build_opening_balances,
)
from pyaccountingkit.domain.journals.journal_entry import EntryStatus
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine


def _line(
    code: str,
    debit: str,
    credit: str,
    *,
    account_id: AccountId | None = None,
) -> AccountBalanceLine:
    return AccountBalanceLine(
        account_id=account_id if account_id is not None else AccountId(f"id:{code}"),
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
        OpeningBalance(
            AccountId("id:411000"),
            "411000",
            Money.from_str("250.00", EUR),
        ),
        OpeningBalance(
            AccountId("id:707000"),
            "707000",
            Money.from_str("-250.00", EUR),
        ),
    )


def test_opening_balances_require_stable_account_identity() -> None:
    line = AccountBalanceLine(
        account_id=None,
        account_code="411000",
        label="Clients",
        sum_debit=Money.from_str("10.00", EUR),
        sum_credit=Money.zero(EUR),
    )

    with pytest.raises(OpeningBalanceIdentityError, match="stable account_id"):
        build_opening_balances((line,))


def test_opening_entry_is_balanced_and_validated_for_canonical_posting() -> None:
    builder = OpeningEntryBuilder(opening_date=date(2025, 1, 1), evidence_run_id="c1")
    entry = builder.build(
        opening_balances=(
            OpeningBalance(
                AccountId("acc:411000"),
                "411000",
                Money.from_str("250.00", EUR),
            ),
            OpeningBalance(
                AccountId("acc:707000"),
                "707000",
                Money.from_str("-250.00", EUR),
            ),
        ),
        journal_id=JournalId("j_ouvert"),
        period_id=PeriodId("p_2025_01"),
        entry_id=EntryId("o1"),
    )
    assert entry.status is EntryStatus.VALIDATED
    assert entry.is_balanced()
    assert "Ouverture depuis clôture c1" in entry.description


def test_unbalanced_opening_rejected() -> None:
    builder = OpeningEntryBuilder(opening_date=date(2025, 1, 1), evidence_run_id="c1")
    with pytest.raises(UnbalancedEntryError):
        builder.build(
            opening_balances=(
                OpeningBalance(
                    AccountId("acc:411000"),
                    "411000",
                    Money.from_str("250.00", EUR),
                ),
            ),
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
