"""Crosswalks — correspondence tables between standards (LOT-10)."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.domain.references.standards import RegulatoryId


@dataclass(frozen=True, slots=True)
class CrosswalkEntry:
    """One directed mapping between two standards for a shared concept."""

    concept_code: str
    source_standard_id: str
    source_node_id: RegulatoryId
    target_standard_id: str
    target_node_id: RegulatoryId


class StandardCrosswalk:
    """Directional correspondence table between standards."""

    def __init__(self, entries: tuple[CrosswalkEntry, ...] = ()) -> None:
        self._entries = tuple(sorted(entries, key=_entry_key))

    def entries(self) -> tuple[CrosswalkEntry, ...]:
        return self._entries

    def add(self, entry: CrosswalkEntry) -> StandardCrosswalk:
        return StandardCrosswalk(self._entries + (entry,))

    def map(
        self,
        source_standard_id: str,
        source_node_id: RegulatoryId,
    ) -> tuple[CrosswalkEntry, ...]:
        return tuple(
            entry
            for entry in self._entries
            if entry.source_standard_id == source_standard_id
            and entry.source_node_id == source_node_id
        )

    def reverse(
        self,
        target_standard_id: str,
        target_node_id: RegulatoryId,
    ) -> tuple[CrosswalkEntry, ...]:
        return tuple(
            entry
            for entry in self._entries
            if entry.target_standard_id == target_standard_id
            and entry.target_node_id == target_node_id
        )

    def entries_for_concept(self, concept_code: str) -> tuple[CrosswalkEntry, ...]:
        return tuple(entry for entry in self._entries if entry.concept_code == concept_code)


def _entry_key(entry: CrosswalkEntry) -> tuple[str, str, str, str]:
    return (
        entry.concept_code,
        entry.source_standard_id,
        entry.target_standard_id,
        entry.source_node_id,
    )


__all__ = ["CrosswalkEntry", "StandardCrosswalk"]
