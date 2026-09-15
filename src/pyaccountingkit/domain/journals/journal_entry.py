"""Deterministic, DRAFT-then-POSTED accounting entries.

``JournalEntry`` is the aggregate root of the journals bounded context. It
enforces the double-entry invariant on construction and is frozen once
created; posting and reversal never mutate an existing entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from pyaccountingkit.core.errors import (
    EmptyEntryError,
    EntryAlreadyPostedError,
    UnbalancedEntryError,
)
from pyaccountingkit.core.identifiers import EntryId, JournalId, PeriodId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.journals.journal_line import JournalLine


class EntryStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


@dataclass(frozen=True)
class JournalEntry:
    """Écriture comptable respectant la règle de la partie double."""

    id: EntryId
    journal_id: JournalId
    period_id: PeriodId
    entry_date: date
    description: str
    lines: tuple[JournalLine, ...]
    status: EntryStatus = EntryStatus.DRAFT
    posted_at: datetime | None = None
    reversal_of_id: EntryId | None = None
    reversed_by_id: EntryId | None = None

    def __post_init__(self) -> None:
        if len(self.lines) < 2:
            raise EmptyEntryError("Une écriture comptable doit comporter au moins 2 lignes")
        if not self.is_balanced():
            raise UnbalancedEntryError(
                f"Écriture déséquilibrée {self.id}: Débit={self.total_debit().amount} "
                f"!= Crédit={self.total_credit().amount}"
            )

    def total_debit(self) -> Money:
        first_currency = self.lines[0].debit.currency
        total = Money.zero(first_currency)
        for line in self.lines:
            total += line.debit
        return total

    def total_credit(self) -> Money:
        first_currency = self.lines[0].credit.currency
        total = Money.zero(first_currency)
        for line in self.lines:
            total += line.credit
        return total

    def is_balanced(self) -> bool:
        """Return ``True`` when debit and credit sums are equal."""
        return self.total_debit() == self.total_credit()

    def validate_balance(self) -> None:
        """Raise ``UnbalancedEntryError`` when the two sides differ."""
        if not self.is_balanced():
            raise UnbalancedEntryError(
                f"Écriture {self.id} déséquilibrée : "
                f"débit {self.total_debit()} ≠ crédit {self.total_credit()}"
            )

    def freeze(self, posted_at: datetime) -> JournalEntry:
        """Return a POSTED copy stamped with the canonical posting time."""
        if self.status is not EntryStatus.DRAFT and self.status is not EntryStatus.VALIDATED:
            raise EntryAlreadyPostedError(
                f"Écriture {self.id} non-DRAFT ({self.status.value}) ne peut être postée"
            )
        return JournalEntry(
            id=self.id,
            journal_id=self.journal_id,
            period_id=self.period_id,
            entry_date=self.entry_date,
            description=self.description,
            lines=self.lines,
            status=EntryStatus.POSTED,
            posted_at=posted_at,
            reversal_of_id=self.reversal_of_id,
            reversed_by_id=self.reversed_by_id,
        )
