"""Golden qualification for OHADA EBNL 2023 and family relations (LOT-27)."""

from __future__ import annotations

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

ROOT = Path(__file__).resolve().parents[3]
REGULATORY = ROOT / "resources" / "regulatory-accounting-data-framework"
STRUCTURED = REGULATORY / "datasets" / "structured"
RELATIONS = REGULATORY / "datasets" / "relations"


def _structure_provider() -> EBNLFilesystemReferenceAdapter:
    return EBNLFilesystemReferenceAdapter(STRUCTURED, clock=FrozenClock())


def _relation_provider() -> OHADARelationFilesystemAdapter:
    return OHADARelationFilesystemAdapter(RELATIONS)


def test_ebnl_2023_full_graph_is_provider_backed_and_grounded() -> None:
    provider = _structure_provider()
    hierarchy = provider.get_hierarchy(StandardType.OHADA_EBNL)

    assert hierarchy.standard_id == "ohada-ebnl"
    assert hierarchy.edition == "2023"
    assert hierarchy.node_count == 1145
    assert [node.ref_code for node in hierarchy.classes()] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
    ]

    scopes = tuple(
        node for node in hierarchy.all_nodes() if node.node_type is ReferenceNodeType.CLASS_SCOPE
    )
    assert len(scopes) == 2
    assert {scope.attributes["scope_id"] for scope in scopes} == {
        "voluntary_contributions",
        "management_accounting",
    }


def test_ebnl_4555_ambiguity_is_preserved_and_lookup_fails_closed() -> None:
    provider = _structure_provider()
    assert provider.get_node(StandardType.OHADA_EBNL, "4555") is None

    first = provider.get_node(
        StandardType.OHADA_EBNL,
        "account:ohada-ebnl:2023:4555:occ01",
    )
    second = provider.get_node(
        StandardType.OHADA_EBNL,
        "account:ohada-ebnl:2023:4555:occ02",
    )
    assert first is not None
    assert second is not None
    assert first.ref_code == second.ref_code == "4555"
    assert first.node_id != second.node_id
    assert first.parent_node_id != second.parent_node_id


def test_ebnl_snapshot_is_deterministic_and_replayable() -> None:
    provider = _structure_provider()
    first = provider.get_snapshot(StandardType.OHADA_EBNL, "2023.1")
    second = provider.get_snapshot(StandardType.OHADA_EBNL, "2023.1")

    assert first.verify()
    assert first.checksum == second.checksum
    assert first.replay().node_count == 1145


def test_ebnl_structure_provider_declares_only_demonstrated_capabilities() -> None:
    capabilities = _structure_provider().capabilities(StandardType.OHADA_EBNL)
    assert capabilities.supports(ReferenceCapability.NODE_LOOKUP)
    assert capabilities.supports(ReferenceCapability.HIERARCHY)
    assert capabilities.supports(ReferenceCapability.SNAPSHOTS)
    assert not capabilities.supports(ReferenceCapability.RELATIONS)
    assert not capabilities.supports(ReferenceCapability.CROSSWALKS)
    assert not capabilities.supports(ReferenceCapability.NEGATIVE_CONSTRAINTS)


def test_ohada_family_relations_are_explicit_and_never_imply_inheritance() -> None:
    provider = _relation_provider()
    ebnl_relations = provider.relations_for("ohada-ebnl:2023")

    relation = next(
        item
        for item in ebnl_relations
        if item.relation_type is ReferenceRelationType.SPECIALIZED_STANDARD_WITHIN_FAMILY
    )
    assert relation.target_ref == "ohada-accounting"
    assert relation.auto_inference_allowed is False
    assert not any(
        item.relation_type is ReferenceRelationType.INHERITS for item in ebnl_relations
    )

    constraint = provider.negative_constraints_for("ohada-ebnl:2023")
    assert len(constraint) == 1
    assert constraint[0].forbidden_relation_type is ReferenceRelationType.INHERITS
    assert constraint[0].target_ref == "ohada-syscohada:2017"

    with pytest.raises(ReferenceRelationInferenceError, match="no explicit inheritance rule"):
        provider.require_auto_inference_allowed(
            "ohada-ebnl:2023",
            ReferenceRelationType.INHERITS,
            "ohada-syscohada:2017",
        )


def test_pcemf_temporal_inheritance_guard_is_runtime_enforced() -> None:
    provider = _relation_provider()
    with pytest.raises(ReferenceRelationInferenceError, match="predates SYSCOHADA 2017"):
        provider.require_auto_inference_allowed(
            "cemac-pcemf:2010",
            ReferenceRelationType.INHERITS,
            "ohada-syscohada:2017",
        )


def test_crosswalk_relation_remains_review_only_and_non_executable() -> None:
    provider = _relation_provider()
    relation = next(
        item
        for item in provider.relations_for("cemac-pcemf:2010")
        if item.relation_type is ReferenceRelationType.CROSSWALK
    )
    assert relation.human_review_required is True
    assert relation.auto_inference_allowed is False

    with pytest.raises(ReferenceRelationInferenceError, match="human review is required"):
        provider.require_auto_inference_allowed(
            "cemac-pcemf:2010",
            ReferenceRelationType.CROSSWALK,
            "ohada-syscohada:2017",
        )
