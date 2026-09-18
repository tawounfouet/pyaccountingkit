"""Immutable public DTOs for journal entries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_entry import JournalEntry
from pyaccountingkit.domain.journals.journal_line import JournalLine


@dataclass(frozen=True, slots=True)
class JournalLineDTO:
    account_id: str
    debit: Money
    credit: Money
    label: str

    @classmethod
    def from_domain(cls, line: JournalLine) -> JournalLineDTO:
        return cls(
            account_id=str(line.account_id),
            debit=line.debit,
            credit=line.credit,
            label=line.label,
        )


@dataclass(frozen=True, slots=True)
class JournalEntryDTO:
    entry_id: str
    journal_id: str
    period_id: str
    entry_date: date
    description: str
    status: str
    lines: tuple[JournalLineDTO, ...]
    posted_at: datetime | None
    reversal_of_id: str | None
    reversed_by_id: str | None

    @classmethod
    def from_domain(cls, entry: JournalEntry) -> JournalEntryDTO:
        return cls(
            entry_id=str(entry.id),
            journal_id=str(entry.journal_id),
            period_id=str(entry.period_id),
            entry_date=entry.entry_date,
            description=entry.description,
            status=entry.status.value,
            lines=tuple(JournalLineDTO.from_domain(line) for line in entry.lines),
            posted_at=entry.posted_at,
            reversal_of_id=str(entry.reversal_of_id) if entry.reversal_of_id else None,
            reversed_by_id=str(entry.reversed_by_id) if entry.reversed_by_id else None,
        )


__all__ = ["JournalEntryDTO", "JournalLineDTO"]
