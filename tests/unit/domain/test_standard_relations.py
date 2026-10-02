"""Domain tests for standard-level regulatory relations (LOT-27)."""

from __future__ import annotations

import pytest

from pyaccountingkit.domain.references.standard_relations import (
    ForbiddenStandardRelation,
    ForbiddenStandardRelationError,
    StandardRelation,
    StandardRelationEvidence,
    StandardRelationInferenceError,
    StandardRelationRegister,
    StandardRelationType,
)


def _register() -> StandardRelationRegister:
    relation = StandardRelation(
        relation_id="ohada-family:ebnl-member",
        relation_type=StandardRelationType.SPECIALIZED_STANDARD_WITHIN_FAMILY,
        subject_ref="ohada-ebnl:2023",
        target_ref="ohada-accounting",
        subject_kind="standard",
        target_kind="family",
        evidence=StandardRelationEvidence(
            source_refs=(),
            note="Explicit family specialization.",
            evidence_status="source_supported",
        ),
        human_review_required=False,
        auto_inference_allowed=False,
    )
    forbidden = ForbiddenStandardRelation(
        constraint_id="no-ebnl-inherits-syscohada-with-current-corpus",
        relation_type=StandardRelationType.INHERITS,
        subject_ref="ohada-ebnl:2023",
        target_ref="ohada-syscohada:2017",
        reason="No inheritance rule is asserted.",
    )
    return StandardRelationRegister(
        "ohada-accounting",
        relations=(relation,),
        negative_constraints=(forbidden,),
    )


def test_forbidden_relation_raises_typed_error() -> None:
    register = _register()
    with pytest.raises(
        ForbiddenStandardRelationError,
        match="no-ebnl-inherits-syscohada-with-current-corpus",
    ):
        register.require_not_forbidden(
            "ohada-ebnl:2023",
            StandardRelationType.INHERITS,
            "ohada-syscohada:2017",
        )


def test_non_forbidden_does_not_mean_auto_inference_allowed() -> None:
    register = _register()
    assert (
        register.can_auto_infer(
            "ohada-ebnl:2023",
            StandardRelationType.SPECIALIZED_STANDARD_WITHIN_FAMILY,
            "ohada-accounting",
        )
        is False
    )
    with pytest.raises(StandardRelationInferenceError, match="not explicitly allowed"):
        register.require_auto_inference_allowed(
            "ohada-ebnl:2023",
            StandardRelationType.SPECIALIZED_STANDARD_WITHIN_FAMILY,
            "ohada-accounting",
        )


def test_missing_relation_is_fail_closed_for_auto_inference() -> None:
    register = _register()
    assert (
        register.can_auto_infer(
            "ohada-ebnl:2023",
            StandardRelationType.CROSSWALK,
            "ohada-syscohada:2017",
        )
        is False
    )


def test_register_rejects_duplicate_relation_ids() -> None:
    relation = _register().all_relations()[0]
    with pytest.raises(ValueError, match="duplicate standard relation_id"):
        StandardRelationRegister(
            "ohada-accounting",
            relations=(relation, relation),
            negative_constraints=(),
        )
