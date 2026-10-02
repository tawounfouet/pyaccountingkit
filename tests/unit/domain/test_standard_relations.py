"""Domain tests for regulatory standard relations (LOT-27)."""

from __future__ import annotations

import pytest

from pyaccountingkit.domain.references.standard_relations import (
    ReferenceNegativeConstraint,
    ReferenceRelation,
    ReferenceRelationEvidence,
    ReferenceRelationInferenceError,
    ReferenceRelationKind,
    ReferenceRelationRegistry,
    ReferenceRelationType,
)


def _relation(
    *,
    relation_type: ReferenceRelationType,
    auto_inference_allowed: bool = False,
    human_review_required: bool = False,
) -> ReferenceRelation:
    return ReferenceRelation(
        relation_id=f"rel:{relation_type.value}",
        relation_type=relation_type,
        subject_ref="ohada-ebnl:2023",
        target_ref="ohada-accounting",
        subject_kind=ReferenceRelationKind.STANDARD,
        target_kind=ReferenceRelationKind.FAMILY,
        evidence=ReferenceRelationEvidence(),
        human_review_required=human_review_required,
        auto_inference_allowed=auto_inference_allowed,
    )


def test_explicit_relation_does_not_imply_automatic_inference() -> None:
    registry = ReferenceRelationRegistry(
        (_relation(relation_type=ReferenceRelationType.SPECIALIZED_STANDARD_WITHIN_FAMILY),),
        (),
    )
    assert registry.relations_for("ohada-ebnl:2023")
    with pytest.raises(ReferenceRelationInferenceError, match="automatic inference is disabled"):
        registry.require_auto_inference_allowed(
            "ohada-ebnl:2023",
            ReferenceRelationType.SPECIALIZED_STANDARD_WITHIN_FAMILY,
            "ohada-accounting",
        )


def test_negative_constraint_blocks_inference_before_relation_lookup() -> None:
    registry = ReferenceRelationRegistry(
        (),
        (
            ReferenceNegativeConstraint(
                constraint_id="no-ebnl-inherits",
                forbidden_relation_type=ReferenceRelationType.INHERITS,
                subject_ref="ohada-ebnl:2023",
                target_ref="ohada-syscohada:2017",
                reason="No explicit inheritance rule is asserted.",
            ),
        ),
    )
    with pytest.raises(ReferenceRelationInferenceError, match="No explicit inheritance rule"):
        registry.require_auto_inference_allowed(
            "ohada-ebnl:2023",
            ReferenceRelationType.INHERITS,
            "ohada-syscohada:2017",
        )


def test_missing_relation_fails_closed() -> None:
    registry = ReferenceRelationRegistry((), ())
    with pytest.raises(ReferenceRelationInferenceError, match="no explicit relation"):
        registry.require_auto_inference_allowed(
            "ohada-ebnl:2023",
            ReferenceRelationType.RELATED_REFERENCE,
            "unknown:standard",
        )


def test_human_review_and_auto_inference_are_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="cannot allow automatic inference"):
        _relation(
            relation_type=ReferenceRelationType.CROSSWALK,
            human_review_required=True,
            auto_inference_allowed=True,
        )
