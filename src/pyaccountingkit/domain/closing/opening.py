"""Opening balances — à-nouveaux entry generated from a closing trial balance."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.errors import DomainError, UnbalancedEntryError
from pyaccountingkit.core.identifiers import AccountId, EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, EntryType, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine


class OpeningBalanceIdentityError(DomainError):
    """Opening generation requires a stable company-account identity."""

    code = "OPENING_ACCOUNT_ID_REQUIRED"


@dataclass(frozen=True, slots=True)
class OpeningBalance:
    """Signed balance carried from a closing trial balance into the next period."""

    account_id: AccountId
    account_code: str
    amount: Money  # positive = debit opening, negative = credit opening

    @property
    def is_debit(self) -> bool:
        return self.amount.amount > 0

    @property
    def is_credit(self) -> bool:
        return self.amount.amount < 0


def build_opening_balances(
    lines: Sequence[AccountBalanceLine],
) -> tuple[OpeningBalance, ...]:
    """Convert trial balance lines into signed opening balances (non-zero only)."""
    openings: list[OpeningBalance] = []
    for line in lines:
        if line.is_zero:
            continue
        if line.account_id is None:
            raise OpeningBalanceIdentityError(
                f"Opening balance {line.account_code!r} has no stable account_id"
            )
        openings.append(
            OpeningBalance(
                account_id=line.account_id,
                account_code=line.account_code,
                amount=line.balance,
            )
        )
    return tuple(openings)


class OpeningEntryBuilder:
    """Builds one balanced `OUVERTURE` journal entry from opening balances."""

    def __init__(
        self,
        opening_date: date,
        evidence_run_id: str,
    ) -> None:
        self._opening_date = opening_date
        self._evidence_run_id = evidence_run_id

    def _make_line(self, balance: OpeningBalance) -> JournalLine:
        if balance.is_debit:
            debit_amount = balance.amount
            credit_amount = Money.zero(balance.amount.currency)
        elif balance.is_credit:
            debit_amount = Money.zero(balance.amount.currency)
            credit_amount = -balance.amount
        else:
            raise UnbalancedEntryError("À-nouveaux nul interdit")
        return JournalLine(
            account_id=balance.account_id,
            debit=debit_amount,
            credit=credit_amount,
            label="Ouverture / à-nouveaux",
        )

    def build(
        self,
        opening_balances: Sequence[OpeningBalance],
        journal_id: JournalId,
        period_id: PeriodId,
        entry_id: EntryId,
    ) -> JournalEntry:
        """Return a VALIDATED opening entry ready for canonical posting."""
        if not opening_balances:
            raise UnbalancedEntryError("Ouverture sans à-nouveaux")
        lines = tuple(self._make_line(balance) for balance in opening_balances)
        if len(lines) < 2:
            raise UnbalancedEntryError("Ouverture déséquilibrée : les à-nouveaux ne compensent pas")
        draft = JournalEntry(
            id=entry_id,
            journal_id=journal_id,
            period_id=period_id,
            entry_date=self._opening_date,
            description=f"Ouverture depuis clôture {self._evidence_run_id}",
            lines=lines,
            entry_type=EntryType.OPENING,
            status=EntryStatus.DRAFT,
            posted_at=None,
        )
        if not draft.is_balanced():
            raise UnbalancedEntryError("Ouverture déséquilibrée : les à-nouveaux ne compensent pas")
        return draft.validate()


__all__ = [
    "OpeningBalance",
    "OpeningBalanceIdentityError",
    "build_opening_balances",
    "OpeningEntryBuilder",
]
