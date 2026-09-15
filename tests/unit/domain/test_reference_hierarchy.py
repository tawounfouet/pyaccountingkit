"""Unit tests for reference hierarchy consumption (LOT-10)."""

from __future__ import annotations

import pytest

from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy, ReferenceNode
from pyaccountingkit.domain.references.standards import ReferenceNodeType


def _node(
    node_id: str,
    ref_code: str,
    *,
    parent: str | None = None,
    node_type: ReferenceNodeType = ReferenceNodeType.ACCOUNT,
    account_class: int | None = 4,
) -> ReferenceNode:
    return ReferenceNode(
        node_id=node_id,
        node_type=node_type,
        standard_id="fr-pcg",
        edition="2026",
        ref_code=ref_code,
        label=node_id,
        account_class=account_class,
        parent_node_id=parent,
    )


def _hierarchy() -> ReferenceHierarchy:
    nodes = (
        _node("c4", "4", node_type=ReferenceNodeType.CLASS, account_class=4),
        _node("g40", "40", parent="c4"),
        _node("a401", "401", parent="g40"),
        _node("a411", "411", parent="g40"),
    )
    return ReferenceHierarchy("fr-pcg", "2026", nodes)


def test_explicit_parent_fields_only() -> None:
    hierarchy = _hierarchy()
    assert str(hierarchy.get_node("g40").parent_node_id) == "c4"


def test_get_node_and_missing() -> None:
    hierarchy = _hierarchy()
    assert hierarchy.get_node("a401") is not None
    assert hierarchy.get_node("missing") is None
    with pytest.raises(KeyError):
        hierarchy.node("missing")


def test_children_and_ancestors() -> None:
    hierarchy = _hierarchy()
    children = [node.node_id for node in hierarchy.children_of("g40")]
    assert children == ["a401", "a411"]
    ancestors = [node.node_id for node in hierarchy.ancestors_of("a401")]
    assert ancestors == ["c4", "g40"]


def test_classes_ordering_by_ref_code() -> None:
    hierarchy = _hierarchy()
    assert [node.ref_code for node in hierarchy.classes()] == ["4"]


def test_class_for() -> None:
    hierarchy = _hierarchy()
    assert hierarchy.class_for("a401").node_id == "c4"
    assert hierarchy.class_for("c4").node_id == "c4"


def test_orphan_node_rejected() -> None:
    nodes = (
        _node("c4", "4", node_type=ReferenceNodeType.CLASS),
        _node("a999", "999", parent="missing"),
    )
    with pytest.raises(ValueError, match="Orphan"):
        ReferenceHierarchy("fr-pcg", "2026", nodes)


def test_duplicate_node_rejected() -> None:
    nodes = (_node("a401", "401"), _node("a401", "402"))
    with pytest.raises(ValueError, match="duplicate"):
        ReferenceHierarchy("fr-pcg", "2026", nodes)
