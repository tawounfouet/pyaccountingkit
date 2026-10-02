"""Relations between regulatory standards and fail-closed inference guards (LOT-27)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReferenceRelationType(StrEnum):
    """Relationship vocabulary published by regulatory reference providers."""

    MEMBER_OF_FAMILY = "member_of_family"
    SECTOR_SPECIALIZATION_WITHIN_FAMILY = "sector_specialization_within_family"
    SPECIALIZED_STANDARD_WITHIN_FAMILY = "specialized_standard_within_family"
    INHERITS = "inherits"
    SUPERSEDES = "supersedes"
    CROSSWALK = "crosswalk"
    RELATED_REFERENCE = "related_reference"


class ReferenceRelationKind(StrEnum):
    STANDARD = "standard"
    FAMILY = "family"


class RelationEvidenceStatus(StrEnum):
    SOURCE_SUPPORTED = "source_supported"
    STRUCTURAL = "structural"
    PENDING_REVIEW = "pending_review"


@dataclass(frozen=True, slots=True)
class ReferenceRelationSource:
    """One optional source pointer supporting a standard relation."""

    document_id: str
    page_pdf: int | None = None
    section: str | None = None
    heading_path: tuple[str, ...] = ()
    snippet: str | None = None

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("relation source document_id must be non-empty")


@dataclass(frozen=True, slots=True)
class ReferenceRelationEvidence:
    """Evidence attached to a relation without turning it into an inference rule."""

    source_refs: tuple[ReferenceRelationSource, ...] = ()
    note: str | None = None
    status: RelationEvidenceStatus = RelationEvidenceStatus.SOURCE_SUPPORTED


@dataclass(frozen=True, slots=True)
class ReferenceRelation:
    """One explicit relation published by the regulatory source."""

    relation_id: str
    relation_type: ReferenceRelationType
    subject_ref: str
    target_ref: str
    subject_kind: ReferenceRelationKind
    target_kind: ReferenceRelationKind
    evidence: ReferenceRelationEvidence
    human_review_required: bool = False
    auto_inference_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.relation_id.strip():
            raise ValueError("relation_id must be non-empty")
        if not self.subject_ref.strip() or not self.target_ref.strip():
            raise ValueError("relation endpoints must be non-empty")
        if self.human_review_required and self.auto_inference_allowed:
            raise ValueError("human-reviewed relation cannot allow automatic inference")


@dataclass(frozen=True, slots=True)
class ReferenceNegativeConstraint:
    """A relation that must never be inferred from the current source corpus."""

    constraint_id: str
    forbidden_relation_type: ReferenceRelationType
    subject_ref: str
    target_ref: str
    reason: str

    def __post_init__(self) -> None:
        if not self.constraint_id.strip():
            raise ValueError("constraint_id must be non-empty")
        if not self.subject_ref.strip() or not self.target_ref.strip():
            raise ValueError("constraint endpoints must be non-empty")
        if not self.reason.strip():
            raise ValueError("negative constraint reason must be non-empty")


class ReferenceRelationInferenceError(ValueError):
    """Raised when runtime code attempts an unproven or forbidden relation inference."""

    def __init__(
        self,
        subject_ref: str,
        relation_type: ReferenceRelationType,
        target_ref: str,
        reason: str,
    ) -> None:
        self.subject_ref = subject_ref
        self.relation_type = relation_type
        self.target_ref = target_ref
        self.reason = reason
        super().__init__(
            f"{subject_ref} --{relation_type.value}--> {target_ref}: {reason}"
        )


class ReferenceRelationRegistry:
    """Immutable relation graph with explicit fail-closed inference semantics."""

    def __init__(
        self,
        relations: tuple[ReferenceRelation, ...],
        negative_constraints: tuple[ReferenceNegativeConstraint, ...],
    ) -> None:
        relation_ids = [relation.relation_id for relation in relations]
        if len(relation_ids) != len(set(relation_ids)):
            raise ValueError("duplicate relation_id")

        constraint_ids = [constraint.constraint_id for constraint in negative_constraints]
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("duplicate relation constraint_id")

        self._relations = tuple(sorted(relations, key=lambda item: item.relation_id))
        self._negative_constraints = tuple(
            sorted(negative_constraints, key=lambda item: item.constraint_id)
        )

    def all_relations(self) -> tuple[ReferenceRelation, ...]:
        return self._relations

    def all_negative_constraints(self) -> tuple[ReferenceNegativeConstraint, ...]:
        return self._negative_constraints

    def relations_for(self, subject_ref: str) -> tuple[ReferenceRelation, ...]:
        return tuple(
            relation for relation in self._relations if relation.subject_ref == subject_ref
        )

    def negative_constraints_for(
        self,
        subject_ref: str,
    ) -> tuple[ReferenceNegativeConstraint, ...]:
        return tuple(
            constraint
            for constraint in self._negative_constraints
            if constraint.subject_ref == subject_ref
        )

    def relation(
        self,
        subject_ref: str,
        relation_type: ReferenceRelationType,
        target_ref: str,
    ) -> ReferenceRelation | None:
        matches = tuple(
            relation
            for relation in self._relations
            if relation.subject_ref == subject_ref
            and relation.relation_type is relation_type
            and relation.target_ref == target_ref
        )
        if len(matches) > 1:
            raise ValueError("multiple relations match the same endpoints and relation type")
        return matches[0] if matches else None

    def negative_constraint(
        self,
        subject_ref: str,
        relation_type: ReferenceRelationType,
        target_ref: str,
    ) -> ReferenceNegativeConstraint | None:
        matches = tuple(
            constraint
            for constraint in self._negative_constraints
            if constraint.subject_ref == subject_ref
            and constraint.forbidden_relation_type is relation_type
            and constraint.target_ref == target_ref
        )
        if len(matches) > 1:
            raise ValueError("multiple negative constraints match the same relation")
        return matches[0] if matches else None

    def require_auto_inference_allowed(
        self,
        subject_ref: str,
        relation_type: ReferenceRelationType,
        target_ref: str,
    ) -> ReferenceRelation:
        """Return the explicit relation only when automatic inference is source-authorized."""
        forbidden = self.negative_constraint(subject_ref, relation_type, target_ref)
        if forbidden is not None:
            raise ReferenceRelationInferenceError(
                subject_ref,
                relation_type,
                target_ref,
                forbidden.reason,
            )

        relation = self.relation(subject_ref, relation_type, target_ref)
        if relation is None:
            raise ReferenceRelationInferenceError(
                subject_ref,
                relation_type,
                target_ref,
                "no explicit relation is published by the provider",
            )
        if relation.human_review_required:
            raise ReferenceRelationInferenceError(
                subject_ref,
                relation_type,
                target_ref,
                "human review is required",
            )
        if not relation.auto_inference_allowed:
            raise ReferenceRelationInferenceError(
                subject_ref,
                relation_type,
                target_ref,
                "automatic inference is disabled by the provider",
            )
        return relation


__all__ = [
    "ReferenceNegativeConstraint",
    "ReferenceRelation",
    "ReferenceRelationEvidence",
    "ReferenceRelationInferenceError",
    "ReferenceRelationKind",
    "ReferenceRelationRegistry",
    "ReferenceRelationSource",
    "ReferenceRelationType",
    "RelationEvidenceStatus",
]
