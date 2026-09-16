"""Explicit link from subledger state to an actually posted GL entry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pyaccountingkit.core.identifiers import EntityId, EntryId
from pyaccountingkit.domain.journals.journal_entry import EntryStatus, JournalEntry
from pyaccountingkit.domain.subledgers.errors import SubledgerAccountingLinkError


@dataclass(frozen=True, slots=True)
class PostedAccountingReference:
    """Proof that a subledger accounting effect points to a POSTED entry."""

    entity_id: EntityId
    entry_id: EntryId
    posted_at: datetime

    @classmethod
    def from_posted_entry(
        cls,
        entry: JournalEntry,
        *,
        entry_entity_id: EntityId,
    ) -> PostedAccountingReference:
        if entry.status is not EntryStatus.POSTED or entry.posted_at is None:
            raise SubledgerAccountingLinkError(
                f"journal entry {entry.id!s} must be POSTED before linking subledger state"
            )
        return cls(
            entity_id=entry_entity_id,
            entry_id=entry.id,
            posted_at=entry.posted_at,
        )


__all__ = ["PostedAccountingReference"]
