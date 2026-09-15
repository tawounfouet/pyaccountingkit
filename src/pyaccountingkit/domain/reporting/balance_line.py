"""Signed per-account balance line inside a trial balance."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.identifiers import AccountId
from pyaccountingkit.core.money import Money


@dataclass(frozen=True, slots=True)
class AccountBalanceLine:
    """One account's aggregated debit/credit sums and signed balance."""

    account_code: str
    label: str
    sum_debit: Money
    sum_credit: Money
    account_id: AccountId | None = None

    @property
    def balance(self) -> Money:
        """Signed balance: positive = net debit, negative = net credit."""
        return self.sum_debit - self.sum_credit

    @property
    def company_account_identity(self) -> str:
        """Stable mapping identity, falling back to code for legacy/synthetic balances."""
        return str(self.account_id) if self.account_id is not None else self.account_code

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
