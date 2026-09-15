"""Signed per-account balance line inside a trial balance."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.money import Money


@dataclass(frozen=True, slots=True)
class AccountBalanceLine:
    """One account's aggregated debit/credit sums and signed balance."""

    account_code: str
    label: str
    sum_debit: Money
    sum_credit: Money

    @property
    def balance(self) -> Money:
        """Signed balance: positive = net debit, negative = net credit."""
        return self.sum_debit - self.sum_credit

    @property
    def is_debit_balance(self) -> bool:
        return self.balance.amount > 0

    @property
    def is_credit_balance(self) -> bool:
        return self.balance.amount < 0

    @property
    def is_zero(self) -> bool:
        return self.balance.amount.is_zero()


__all__ = ["AccountBalanceLine"]
