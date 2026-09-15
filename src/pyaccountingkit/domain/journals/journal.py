"""Journal definition of the journals bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.identifiers import EntityId, JournalId


@dataclass(frozen=True, slots=True)
class Journal:
    """A postable accounting journal (Ventes, Achats, Banque, OD, ...)."""

    id: JournalId
    entity_id: EntityId
    code: str
    label: str
    active: bool = True

    def is_active(self) -> bool:
        return self.active

    def deactivated(self) -> Journal:
        """Return an inactive copy (journals are immutable)."""
        if not self.active:
            return self
        return Journal(
            id=self.id,
            entity_id=self.entity_id,
            code=self.code,
            label=self.label,
            active=False,
        )


__all__ = ["Journal"]
