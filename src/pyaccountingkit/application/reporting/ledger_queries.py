"""Journal and general-ledger run queries (LOT-07)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.ports.unit_of_work import UnitOfWorkFactoryProtocol


def _chronological(entries: Sequence[JournalEntry]) -> tuple[JournalEntry, ...]:
    return tuple(sorted(entries, key=lambda entry: (entry.entry_date, str(entry.id))))


class JournalQuery:
    """Reads POSTED entries of one journal in deterministic order."""

    def __init__(self, uow_factory: UnitOfWorkFactoryProtocol) -> None:
        self._uow_factory = uow_factory

    def entries_for(
        self,
        journal_id: JournalId,
        period_id: PeriodId | None = None,
    ) -> Sequence[JournalEntry]:
        """Return posted entries of a journal, optionally filtered by period."""
        with self._uow_factory.open() as uow:
            entries = uow.entries.list_by_journal(journal_id)
            if period_id is not None:
                entries = [e for e in entries if e.period_id == period_id]
            return _chronological(entries)


@dataclass(frozen=True, slots=True)
class LedgerPosition:
    """One posted line with its running signed balance for the account."""

    account_code: str
    entry_id: str
    entry_date: date
    debit: Money
    credit: Money
    running_balance: Money


class GeneralLedgerQuery:
    """Computes per-account running balances over a period's posted entries."""

    def __init__(self, uow_factory: UnitOfWorkFactoryProtocol) -> None:
        self._uow_factory = uow_factory
        self._currency = EUR

    def account_ledger(
        self,
        period_id: PeriodId,
        account_code: str,
    ) -> Sequence[LedgerPosition]:
        """Return, in chronological order, the positions of one account."""
        with self._uow_factory.open() as uow:
            entries = _chronological(uow.entries.list_by_period(period_id))
        running = Money.zero(self._currency)
        positions: list[LedgerPosition] = []
        for entry in entries:
            for line in entry.lines:
                if str(line.account_id) != account_code:
                    continue
                running = running + line.debit - line.credit
                positions.append(
                    LedgerPosition(
                        account_code=account_code,
                        entry_id=str(entry.id),
                        entry_date=entry.entry_date,
                        debit=line.debit,
                        credit=line.credit,
                        running_balance=running,
                    )
                )
        return tuple(positions)


__all__ = ["JournalQuery", "GeneralLedgerQuery", "LedgerPosition"]
