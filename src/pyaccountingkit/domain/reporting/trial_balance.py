"""Trial balance snapshot — the aggregated, double-entry-verified summary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pyaccountingkit.core.currency import EUR, Currency
from pyaccountingkit.core.errors import UnbalancedEntryError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.traceability.trace import CanonicalHasher


class TrialBalanceSnapshot(StrEnum):
    BEFORE_ADJUSTMENTS = "BEFORE_ADJUSTMENTS"
    ADJUSTED = "ADJUSTED"
    POST_CLOSING = "POST_CLOSING"


@dataclass(frozen=True, slots=True)
class TrialBalance:
    """Sum-of-lines per account, sorted by account code, for one period/snapshot."""

    period_id: str
    snapshot: TrialBalanceSnapshot
    lines: tuple[AccountBalanceLine, ...]
    total_debit: Money
    total_credit: Money
    checksum: str
    accounting_entity_id: EntityId | None = None

    def __post_init__(self) -> None:
        if self.total_debit != self.total_credit:
            raise UnbalancedEntryError(
                f"Balance générale déséquilibrée : débit {self.total_debit.amount} "
                f"≠ crédit {self.total_credit.amount}"
            )

    @property
    def currency(self) -> Currency:
        """Currency of the verified trial-balance totals."""
        return self.total_debit.currency

    def lines_for_account(self, account_code: str) -> AccountBalanceLine:
        """Return the single balance line for *account_code*."""
        for line in self.lines:
            if line.account_code == account_code:
                return line
        raise KeyError(account_code)

    @classmethod
    def build(
        cls,
        period_id: str,
        snapshot: TrialBalanceSnapshot,
        lines: tuple[AccountBalanceLine, ...],
        *,
        accounting_entity_id: EntityId | None = None,
    ) -> TrialBalance:
        """Construct a trial balance, validating equality and computing the checksum."""
        sorted_lines = tuple(
            sorted(
                lines,
                key=lambda item: (
                    item.account_code,
                    item.company_account_identity,
                ),
            )
        )
        currency = sorted_lines[0].sum_debit.currency if sorted_lines else EUR
        total_debit = Money.zero(currency)
        total_credit = Money.zero(currency)
        for line in sorted_lines:
            total_debit = total_debit + line.sum_debit
            total_credit = total_credit + line.sum_credit
        checksum = CanonicalHasher.digest(
            {
                "period_id": period_id,
                "snapshot": snapshot.value,
                "accounting_entity_id": (
                    str(accounting_entity_id) if accounting_entity_id is not None else None
                ),
                "lines": [
                    {
                        "account_id": (
                            str(line.account_id) if line.account_id is not None else None
                        ),
                        "account_code": line.account_code,
                        "company_account_identity": line.company_account_identity,
                        "sum_debit": {
                            "amount": str(line.sum_debit.amount),
                            "currency": line.sum_debit.currency.code,
                            "exponent": line.sum_debit.currency.exponent,
                        },
                        "sum_credit": {
                            "amount": str(line.sum_credit.amount),
                            "currency": line.sum_credit.currency.code,
                            "exponent": line.sum_credit.currency.exponent,
                        },
                    }
                    for line in sorted_lines
                ],
            }
        )
        return cls(
            period_id=period_id,
            snapshot=snapshot,
            lines=sorted_lines,
            total_debit=total_debit,
            total_credit=total_credit,
            checksum=checksum,
            accounting_entity_id=accounting_entity_id,
        )


__all__ = ["TrialBalance", "TrialBalanceSnapshot"]
