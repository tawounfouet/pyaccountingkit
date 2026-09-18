"""Immutable public DTOs for trial-balance reads."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.reporting.trial_balance import TrialBalance


@dataclass(frozen=True, slots=True)
class TrialBalanceLineDTO:
    account_id: str
    account_code: str
    label: str
    debit: Money
    credit: Money
    balance: Money

    @classmethod
    def from_domain(cls, line: AccountBalanceLine) -> TrialBalanceLineDTO:
        return cls(
            account_id=str(line.account_id),
            account_code=line.account_code,
            label=line.label,
            debit=line.sum_debit,
            credit=line.sum_credit,
            balance=line.balance,
        )


@dataclass(frozen=True, slots=True)
class TrialBalanceDTO:
    period_id: str
    snapshot: str
    accounting_entity_id: str | None
    total_debit: Money
    total_credit: Money
    checksum: str
    lines: tuple[TrialBalanceLineDTO, ...]

    @classmethod
    def from_domain(cls, balance: TrialBalance) -> TrialBalanceDTO:
        return cls(
            period_id=balance.period_id,
            snapshot=balance.snapshot.value,
            accounting_entity_id=(
                str(balance.accounting_entity_id)
                if balance.accounting_entity_id is not None
                else None
            ),
            total_debit=balance.total_debit,
            total_credit=balance.total_credit,
            checksum=balance.checksum,
            lines=tuple(TrialBalanceLineDTO.from_domain(line) for line in balance.lines),
        )


__all__ = ["TrialBalanceDTO", "TrialBalanceLineDTO"]
