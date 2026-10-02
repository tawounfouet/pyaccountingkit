"""Golden qualification for OHADA family relations and negative constraints."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyaccountingkit.adapters.regulatory.ohada import (
    OHADAStandardRelationFilesystemAdapter,
)
from pyaccountingkit.application.references.standard_relation_service import (
    StandardRelationService,
)
from pyaccountingkit.domain.references.standard_relations import (
    ForbiddenStandardRelationError,
    StandardRelationInferenceError,
    StandardRelationType,
)
from pyaccountingkit import AccountingApplication

RELATIONS = (
    Path(__file__).resolve().parents[3]
    / "resources"
    / "regulatory-accounting-data-framework"
    / "datasets"
    / "relations"
)


def _provider() -> OHADAStandardRelationFilesystemAdapter:
    return OHADAStandardRelationFilesystemAdapter(RELATIONS)


def test_ohada_relation_register_matches_canonical_corpus() -> None:
    register = _provider().relation_register()
    assert register.family_id == "ohada-accounting"
    assert len(register.all_relations()) == 4
    assert len(register.all_negative_constraints()) == 2


def test_ebnl_is_specialized_family_member_not_syscohada_inheritance() -> None:
    provider = _provider()
    relations = provider.relations_for(
        "ohada-ebnl:2023",
        StandardRelationType.SPECIALIZED_STANDARD_WITHIN_FAMILY,
    )
    assert len(relations) == 1
    assert relations[0].target_ref == "ohada-accounting"
    assert relations[0].auto_inference_allowed is False

    assert (
        provider.can_auto_infer(
            "ohada-ebnl:2023",
            StandardRelationType.INHERITS,
            "ohada-syscohada:2017",
        )
        is False
    )
    with pytest.raises(
        ForbiddenStandardRelationError,
        match="no-ebnl-inherits-syscohada-with-current-corpus",
    ):
        provider.require_not_forbidden(
            "ohada-ebnl:2023",
            StandardRelationType.INHERITS,
            "ohada-syscohada:2017",
        )


def test_pcemf_cannot_inherit_from_later_syscohada() -> None:
    provider = _provider()
    with pytest.raises(
        ForbiddenStandardRelationError,
        match="no-pcemf2010-inherits-syscohada2017",
    ):
        provider.require_not_forbidden(
            "cemac-pcemf:2010",
            StandardRelationType.INHERITS,
            "ohada-syscohada:2017",
        )


def test_crosswalk_scope_remains_review_only_and_non_inferable() -> None:
    provider = _provider()
    relations = provider.relations_for(
        "cemac-pcemf:2010",
        StandardRelationType.CROSSWALK,
    )
    assert len(relations) == 1
    assert relations[0].human_review_required is True
    assert relations[0].auto_inference_allowed is False

    with pytest.raises(StandardRelationInferenceError):
        provider.require_auto_inference_allowed(
            "cemac-pcemf:2010",
            StandardRelationType.CROSSWALK,
            "ohada-syscohada:2017",
        )


def test_public_references_facade_can_apply_relation_guard() -> None:
    application = AccountingApplication(references=StandardRelationService(_provider()))
    assert (
        application.references.can_auto_infer(
            subject_ref="ohada-ebnl:2023",
            relation_type=StandardRelationType.SPECIALIZED_STANDARD_WITHIN_FAMILY,
            target_ref="ohada-accounting",
        )
        is False
    )
