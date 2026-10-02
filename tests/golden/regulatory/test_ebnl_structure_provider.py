"""Golden qualification for the OHADA EBNL 2023 structure provider."""

from __future__ import annotations

from pathlib import Path

from pyaccountingkit.adapters.regulatory.ohada import EBNLFilesystemReferenceAdapter
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.domain.references.capabilities import ReferenceCapability
from pyaccountingkit.domain.references.standards import ReferenceNodeType, StandardType

STRUCTURED = (
    Path(__file__).resolve().parents[3]
    / "resources"
    / "regulatory-accounting-data-framework"
    / "datasets"
    / "structured"
)


def _provider() -> EBNLFilesystemReferenceAdapter:
    return EBNLFilesystemReferenceAdapter(STRUCTURED, clock=FrozenClock())


def test_ebnl_structure_preserves_full_reviewed_graph() -> None:
    hierarchy = _provider().get_hierarchy(StandardType.OHADA_EBNL)
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


def test_ebnl_class_nine_scopes_remain_explicit_nodes() -> None:
    hierarchy = _provider().get_hierarchy(StandardType.OHADA_EBNL)
    scopes = tuple(
        node
        for node in hierarchy.all_nodes()
        if node.node_type is ReferenceNodeType.CLASS_SCOPE
    )
    assert len(scopes) == 2
    assert {node.attributes["scope_id"] for node in scopes} == {
        "voluntary_contributions",
        "management_accounting",
    }

    group_90 = _provider().get_node(StandardType.OHADA_EBNL, "90")
    group_92 = _provider().get_node(StandardType.OHADA_EBNL, "92")
    assert group_90 is not None
    assert group_92 is not None
    assert group_90.parent_node_id == "class-scope:ohada-ebnl:2023:9:voluntary_contributions"
    assert group_92.parent_node_id == "class-scope:ohada-ebnl:2023:9:management_accounting"


def test_ebnl_duplicate_4555_is_not_collapsed_or_guessed() -> None:
    provider = _provider()
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
    assert first.node_id != second.node_id
    assert first.ref_code == second.ref_code == "4555"
    assert first.parent_node_id != second.parent_node_id


def test_ebnl_snapshot_is_deterministic_and_replayable() -> None:
    provider = _provider()
    first = provider.get_snapshot(StandardType.OHADA_EBNL, "2023.1")
    second = provider.get_snapshot(StandardType.OHADA_EBNL, "2023.1")
    assert first.verify()
    assert second.verify()
    assert first.checksum == second.checksum
    assert first.replay().node_count == 1145


def test_ebnl_provider_declares_structure_capabilities_only() -> None:
    capabilities = _provider().capabilities(StandardType.OHADA_EBNL)
    assert capabilities.supports(ReferenceCapability.NODE_LOOKUP)
    assert capabilities.supports(ReferenceCapability.HIERARCHY)
    assert capabilities.supports(ReferenceCapability.SNAPSHOTS)
    assert not capabilities.supports(ReferenceCapability.CROSSWALKS)
    assert not capabilities.supports(ReferenceCapability.CONCEPTS)
