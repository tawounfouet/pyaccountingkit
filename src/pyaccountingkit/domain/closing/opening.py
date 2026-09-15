"""Opening balances — à-nouveaux entry generated from a closing trial balance."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.errors import UnbalancedEntryError
from pyaccountingkit.core.identifiers import AccountId, EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine


@dataclass(frozen=True, slots=True)
class OpeningBalance:
    """Signed balance carried from a closing trial balance into the next period."""

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
    return tuple(
        OpeningBalance(account_code=line.account_code, amount=line.balance)
        for line in lines
        if not line.is_zero
    )


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
            account_id=AccountId(balance.account_code),
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
        """Return the POSTED opening entry if the balances balance exactly."""
        if not opening_balances:
            raise UnbalancedEntryError("Ouverture sans à-nouveaux")
        lines = tuple(self._make_line(balance) for balance in opening_balances)
        if len(lines) < 2:
            raise UnbalancedEntryError("Ouverture déséquilibrée : les à-nouveaux ne compensent pas")
        entry = JournalEntry(
            id=entry_id,
            journal_id=journal_id,
            period_id=period_id,
            entry_date=self._opening_date,
            description=f"Ouverture depuis clôture {self._evidence_run_id}",
            lines=lines,
            status=EntryStatus.POSTED,
            posted_at=None,
        )
        if not entry.is_balanced():
            raise UnbalancedEntryError("Ouverture déséquilibrée : les à-nouveaux ne compensent pas")
        return entry


__all__ = ["OpeningBalance", "build_opening_balances", "OpeningEntryBuilder"]
