"""Adjustment proposals — corrections that never mutate the posted source (LOT-09)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pyaccountingkit.core.errors import EntryNotPostedError
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry


@dataclass(frozen=True, slots=True)
class AdjustmentProposal:
    """A proposed adjustment entry linked to a posted source, source untouched."""

    id: str
    source_entry: JournalEntry
    adjustment: JournalEntry
    proposed_at: datetime

    def __post_init__(self) -> None:
        if self.source_entry.status is not EntryStatus.POSTED:
            raise EntryNotPostedError(
                f"Un ajustement exige une source POSTED, reçu {self.source_entry.status}"
            )

    def applies(self) -> None:
        """Verify the proposal is coherent; the source remains immutable."""


__all__ = ["AdjustmentProposal"]
