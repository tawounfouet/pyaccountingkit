"""Unit tests for the OHADA standard relation filesystem provider."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyaccountingkit.adapters.regulatory.ohada import (
    OHADAStandardRelationFilesystemAdapter,
    parse_standard_relation_register,
)
from pyaccountingkit.domain.references.standard_relations import (
    ForbiddenStandardRelationError,
    StandardRelationInferenceError,
    StandardRelationType,
)


def test_relation_parser_preserves_review_and_inference_flags() -> None:
    document = {
        "family_id": "ohada-accounting",
        "relations": [
            {
                "relation_id": "crosswalk",
                "relation_type": "crosswalk",
                "subject_ref": "cemac-pcemf:2010",
                "target_ref": "ohada-syscohada:2017",
                "subject_kind": "standard",
                "target_kind": "standard",
                "evidence": {
                    "source_refs": [],
                    "note": "Candidate crosswalk.",
                    "evidence_status": "structural",
                },
                "human_review_required": True,
                "auto_inference_allowed": False,
            }
        ],
        "negative_constraints": [
            {
                "constraint_id": "no-inheritance",
                "forbidden_relation_type": "inherits",
                "subject_ref": "cemac-pcemf:2010",
                "target_ref": "ohada-syscohada:2017",
                "reason": "Chronology forbids the inference.",
            }
        ],
    }
    register = parse_standard_relation_register(document)
    relation = register.all_relations()[0]
    assert relation.human_review_required is True
    assert relation.auto_inference_allowed is False
    assert relation.relation_type is StandardRelationType.CROSSWALK

    with pytest.raises(ForbiddenStandardRelationError, match="no-inheritance"):
        register.require_not_forbidden(
            "cemac-pcemf:2010",
            StandardRelationType.INHERITS,
            "ohada-syscohada:2017",
        )


def test_filesystem_provider_is_fail_closed_without_explicit_auto_inference(
    tmp_path: Path,
) -> None:
    document = {
        "family_id": "ohada-accounting",
        "relations": [],
        "negative_constraints": [],
    }
    (tmp_path / "relations.json").write_text(json.dumps(document), encoding="utf-8")
    provider = OHADAStandardRelationFilesystemAdapter(
        tmp_path,
        filename="relations.json",
    )

    assert (
        provider.can_auto_infer(
            "ohada-ebnl:2023",
            StandardRelationType.INHERITS,
            "ohada-syscohada:2017",
        )
        is False
    )
    with pytest.raises(StandardRelationInferenceError):
        provider.require_auto_inference_allowed(
            "ohada-ebnl:2023",
            StandardRelationType.INHERITS,
            "ohada-syscohada:2017",
        )
