"""Unit tests for EBNL structure and OHADA relation providers (LOT-27)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyaccountingkit.adapters.regulatory.ebnl import EBNLFilesystemReferenceAdapter
from pyaccountingkit.adapters.regulatory.ohada_relations import (
    OHADARelationFilesystemAdapter,
)
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.domain.references.capabilities import ReferenceCapability
from pyaccountingkit.domain.references.standard_relations import (
    ReferenceRelationInferenceError,
    ReferenceRelationType,
)
from pyaccountingkit.domain.references.standards import ReferenceNodeType, StandardType


def test_ebnl_provider_supports_class_scope_without_false_extra_capabilities(
    tmp_path: Path,
) -> None:
    document = {
        "standard_id": "ohada-ebnl",
        "edition": "2023",
        "nodes": [
            {
                "account_class": 9,
                "attributes": {},
                "edition": "2023",
                "is_leaf": False,
                "label_source": "Classe 9",
                "node_id": "class:ohada-ebnl:2023:9",
                "node_type": "class",
                "parent_node_id": None,
                "ref_code": "9",
                "standard_id": "ohada-ebnl",
            },
            {
                "account_class": 9,
                "attributes": {"scope_id": "management_accounting"},
                "edition": "2023",
                "is_leaf": False,
                "label_source": "Comptabilité analytique",
                "node_id": "class-scope:ohada-ebnl:2023:9:management_accounting",
                "node_type": "class_scope",
                "parent_node_id": "class:ohada-ebnl:2023:9",
                "ref_code": "9",
                "standard_id": "ohada-ebnl",
            },
        ],
    }
    (tmp_path / "ebnl.json").write_text(json.dumps(document), encoding="utf-8")
    provider = EBNLFilesystemReferenceAdapter(
        tmp_path,
        clock=FrozenClock(),
        filename="ebnl.json",
    )

    hierarchy = provider.get_hierarchy(StandardType.OHADA_EBNL)
    scope = hierarchy.node("class-scope:ohada-ebnl:2023:9:management_accounting")
    assert scope.node_type is ReferenceNodeType.CLASS_SCOPE

    capabilities = provider.capabilities(StandardType.OHADA_EBNL)
    assert capabilities.supports(ReferenceCapability.NODE_LOOKUP)
    assert capabilities.supports(ReferenceCapability.HIERARCHY)
    assert capabilities.supports(ReferenceCapability.SNAPSHOTS)
    assert not capabilities.supports(ReferenceCapability.RELATIONS)
    assert not capabilities.supports(ReferenceCapability.NEGATIVE_CONSTRAINTS)


def test_ohada_relation_provider_exposes_and_enforces_negative_constraints(
    tmp_path: Path,
) -> None:
    document = {
        "family_id": "ohada-accounting",
        "relations": [
            {
                "relation_id": "ohada-family:ebnl-member",
                "relation_type": "specialized_standard_within_family",
                "subject_ref": "ohada-ebnl:2023",
                "target_ref": "ohada-accounting",
                "subject_kind": "standard",
                "target_kind": "family",
                "evidence": {
                    "source_refs": [],
                    "note": "Specialized standard.",
                    "evidence_status": "source_supported",
                },
                "human_review_required": False,
                "auto_inference_allowed": False,
            }
        ],
        "negative_constraints": [
            {
                "constraint_id": "no-ebnl-inherits",
                "forbidden_relation_type": "inherits",
                "subject_ref": "ohada-ebnl:2023",
                "target_ref": "ohada-syscohada:2017",
                "reason": "No inheritance rule.",
            }
        ],
    }
    (tmp_path / "relations.json").write_text(json.dumps(document), encoding="utf-8")
    provider = OHADARelationFilesystemAdapter(tmp_path, filename="relations.json")

    capabilities = provider.capabilities("ohada-ebnl:2023")
    assert capabilities.supports(ReferenceCapability.RELATIONS)
    assert capabilities.supports(ReferenceCapability.NEGATIVE_CONSTRAINTS)
    assert len(provider.relations_for("ohada-ebnl:2023")) == 1
    assert len(provider.negative_constraints_for("ohada-ebnl:2023")) == 1

    with pytest.raises(ReferenceRelationInferenceError, match="No inheritance rule"):
        provider.require_auto_inference_allowed(
            "ohada-ebnl:2023",
            ReferenceRelationType.INHERITS,
            "ohada-syscohada:2017",
        )
