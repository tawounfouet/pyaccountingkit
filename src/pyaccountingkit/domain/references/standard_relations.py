"""Relations between regulatory standards and fail-closed negative constraints (LOT-27)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class StandardRelationType(StrEnum):
    """Canonical relation kinds present or guarded by the regulatory corpus."""

    MEMBER_OF_FAMILY = "member_of_family"
    SPECIALIZED_STANDARD_WITHIN_FAMILY = "specialized_standard_within_family"
    SECTOR_SPECIALIZATION_WITHIN_FAMILY = "sector_specialization_within_family"
    CROSSWALK = "crosswalk"
    INHERITS = "inherits"


@dataclass(frozen=True, slots=True)
class RelationEvidenceSource:
    """Source reference supporting a standard-level relation."""

    document_id: str
    section: str
    snippet: str
    page_pdf: int | None = None
    heading_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("relation evidence document_id must be non-empty")
        if not self.section.strip():
            raise ValueError("relation evidence section must be non-empty")
        if not self.snippet.strip():
            raise ValueError("relation evidence snippet must be non-empty")


@dataclass(frozen=True, slots=True)
class StandardRelationEvidence:
    """Evidence envelope attached to one standard relation."""

    source_refs: tuple[RelationEvidenceSource, ...]
    note: str
    evidence_status: str

    def __post_init__(self) -> None:
        if not self.note.strip():
            raise ValueError("relation evidence note must be non-empty")
        if not self.evidence_status.strip():
            raise ValueError("relation evidence status must be non-empty")


@dataclass(frozen=True, slots=True)
class StandardRelation:
    """One explicit relation from the regulatory corpus."""

    relation_id: str
    relation_type: StandardRelationType
    subject_ref: str
    target_ref: str
    subject_kind: str
    target_kind: str
    evidence: StandardRelationEvidence
    human_review_required: bool
    auto_inference_allowed: bool

    def __post_init__(self) -> None:
        required = (
            self.relation_id,
            self.subject_ref,
            self.target_ref,
            self.subject_kind,
            self.target_kind,
        )
        if any(not value.strip() for value in required):
            raise ValueError("standard relation identity fields must be non-empty")
        if self.human_review_required and self.auto_inference_allowed:
            raise ValueError("human-reviewed relation cannot allow automatic inference")


@dataclass(frozen=True, slots=True)
class ForbiddenStandardRelation:
    """Explicit prohibition against one standard-to-standard inference."""

    constraint_id: str
    relation_type: StandardRelationType
    subject_ref: str
    target_ref: str
    reason: str

    def __post_init__(self) -> None:
        required = (
            self.constraint_id,
            self.subject_ref,
            self.target_ref,
            self.reason,
        )
        if any(not value.strip() for value in required):
            raise ValueError("forbidden relation fields must be non-empty")


class ForbiddenStandardRelationError(ValueError):
    """Raised when a caller attempts an explicitly forbidden regulatory inference."""


class StandardRelationRegister:
    """Immutable query and guard surface for one regulatory standard family."""

    def __init__(
        self,
        family_id: str,
        relations: tuple[StandardRelation, ...],
        negative_constraints: tuple[ForbiddenStandardRelation, ...],
    ) -> None:
        if not family_id.strip():
            raise ValueError("relation family_id must be non-empty")
        relation_ids = [relation.relation_id for relation in relations]
        constraint_ids = [constraint.constraint_id for constraint in negative_constraints]
        if len(relation_ids) != len(set(relation_ids)):
            raise ValueError("duplicate standard relation_id")
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("duplicate forbidden relation constraint_id")

        self._family_id = family_id
        self._relations = relations
        self._negative_constraints = negative_constraints

    @property
    def family_id(self) -> str:
        return self._family_id

    def all_relations(self) -> tuple[StandardRelation, ...]:
        return self._relations

    def all_negative_constraints(self) -> tuple[ForbiddenStandardRelation, ...]:
        return self._negative_constraints

    def relations_for(
        self,
        subject_ref: str,
        relation_type: StandardRelationType | None = None,
    ) -> tuple[StandardRelation, ...]:
        return tuple(
            relation
            for relation in self._relations
            if relation.subject_ref == subject_ref
            and (relation_type is None or relation.relation_type is relation_type)
        )

    def negative_constraints_for(
        self,
        subject_ref: str,
    ) -> tuple[ForbiddenStandardRelation, ...]:
        return tuple(
            constraint
            for constraint in self._negative_constraints
            if constraint.subject_ref == subject_ref
        )

    def forbidden_constraint(
        self,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
    ) -> ForbiddenStandardRelation | None:
        for constraint in self._negative_constraints:
            if (
                constraint.subject_ref == subject_ref
                and constraint.relation_type is relation_type
                and constraint.target_ref == target_ref
            ):
                return constraint
        return None

    def require_allowed(
        self,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
    ) -> None:
        constraint = self.forbidden_constraint(subject_ref, relation_type, target_ref)
        if constraint is not None:
            raise ForbiddenStandardRelationError(
                f"{constraint.constraint_id}: {constraint.reason}"
            )

    def can_auto_infer(
        self,
        subject_ref: str,
        relation_type: StandardRelationType,
        target_ref: str,
    ) -> bool:
        self.require_allowed(subject_ref, relation_type, target_ref)
        return any(
            relation.target_ref == target_ref and relation.auto_inference_allowed
            for relation in self.relations_for(subject_ref, relation_type)
        )


__all__ = [
    "ForbiddenStandardRelation",
    "ForbiddenStandardRelationError",
    "RelationEvidenceSource",
    "StandardRelation",
    "StandardRelationEvidence",
    "StandardRelationRegister",
    "StandardRelationType",
]
