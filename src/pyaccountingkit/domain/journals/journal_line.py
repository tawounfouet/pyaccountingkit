"""Single accounting line of a journal entry.

A line either debits or credits one account. Per the universal line
invariants (INV-LINE-001..003) a validated line is non-negative, never
debits and credits at the same time, and is never entirely null.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.errors import (
    DebitAndCreditSetError,
    NegativeAmountError,
    ZeroLineError,
)
from pyaccountingkit.core.identifiers import AccountId
from pyaccountingkit.core.money import Money


@dataclass(frozen=True, slots=True)
class JournalLine:
    """One debit-or-credit line of a ``JournalEntry``."""

    account_id: AccountId
    debit: Money
    credit: Money
    label: str = ""

    def __post_init__(self) -> None:
        if not self.debit.is_same_currency(self.credit):
            raise ValueError("Une ligne comptable est monocurrence")
        if self.debit.amount < 0 or self.credit.amount < 0:
            raise NegativeAmountError(f"Montant négatif interdit sur la ligne {self.account_id}")
        if self.debit.amount > 0 and self.credit.amount > 0:
            raise DebitAndCreditSetError(
                f"Débit et crédit ne peuvent pas être simultanés sur {self.account_id}"
            )

    @property
    def currency(self) -> Currency:
        """The line currency (same Money carries it on both sides)."""
        return self.debit.currency

    def validate_not_null(self) -> None:
        """Reject an entirely null line (INV-LINE-003, applied at validation)."""
        if self.debit.is_zero() and self.credit.is_zero():
            raise ZeroLineError(f"Ligne entièrement nulle sur {self.account_id}")


__all__ = ["JournalLine"]
