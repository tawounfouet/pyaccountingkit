"""Crosswalks — correspondence tables between standards (LOT-10)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

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



# LOT-27 reviewed structural candidates are deliberately distinct from executable StandardCrosswalk.


class CrosswalkCandidateStatus(StrEnum):
    SYSCOHADA_ONLY_CODE = "syscohada_only_code"
    EBNL_ONLY_CODE = "ebnl_only_code"
    SAME_CODE_LABEL_VARIATION = "same_code_label_variation"
    SAME_CODE_SAME_NORMALIZED_LABEL = "same_code_same_normalized_label"
    AMBIGUOUS_EBNL_SOURCE_CODE = "ambiguous_ebnl_source_code"


@dataclass(frozen=True, slots=True)
class CrosswalkOccurrence:
    record_id: str
    label: str
    page_pdf: int
    source_group_context: str | None = None


@dataclass(frozen=True, slots=True)
class StructuralCrosswalkCandidate:
    ref_code: str
    status: CrosswalkCandidateStatus
    syscohada_label: str | None
    ebnl_occurrences: tuple[CrosswalkOccurrence, ...]
    human_review_required: bool
    semantic_equivalence_asserted: bool

    @property
    def executable(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class ReviewedStructuralCrosswalk:
    comparison_id: str
    relation_type: str
    rows: tuple[StructuralCrosswalkCandidate, ...]
    automatic_crosswalk_approval: bool
    human_review_required_for_semantics: bool
    inheritance_asserted: bool
    semantic_equivalence_from_code_equality: bool

    def __post_init__(self) -> None:
        if self.automatic_crosswalk_approval:
            raise ValueError("structural crosswalk cannot enable automatic approval")
        if self.inheritance_asserted or self.semantic_equivalence_from_code_equality:
            raise ValueError("structural evidence cannot assert semantic equivalence")
        if any(row.semantic_equivalence_asserted for row in self.rows):
            raise ValueError("structural crosswalk rows cannot assert semantic equivalence")

    def candidates_for(self, ref_code: str) -> tuple[StructuralCrosswalkCandidate, ...]:
        return tuple(row for row in self.rows if row.ref_code == ref_code)

    def require_executable_mapping(self, ref_code: str) -> None:
        if self.candidates_for(ref_code):
            raise PermissionError(
                f"{ref_code!r} is a structural candidate and requires reviewed semantic evidence"
            )
        raise KeyError(ref_code)


__all__ = [
    "CrosswalkCandidateStatus",
    "CrosswalkEntry",
    "CrosswalkOccurrence",
    "ReviewedStructuralCrosswalk",
    "StandardCrosswalk",
    "StructuralCrosswalkCandidate",
]
