"""Reference nodes and hierarchy — explicit fields from the datasets (LOT-10).

The hierarchy is consumed strictly from the explicit dataset fields
(``node_id``, ``parent_node_id``, ``node_type``...): parent relations are
never *inferred* from a code prefix (DoD ``hierarchy consumed from explicit
dataset fields``).  Regulatory ids are preserved exactly as published.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from pyaccountingkit.domain.references.standards import ReferenceNodeType, RegulatoryId


@dataclass(frozen=True, slots=True)
class ReferenceNode:
    """One official node of a regulatory chart of accounts."""

    node_id: RegulatoryId
    node_type: ReferenceNodeType
    standard_id: str
    edition: str
    ref_code: str
    label: str
    account_class: int | None = None
    parent_node_id: RegulatoryId | None = None
    is_leaf: bool = False
    attributes: Mapping[str, object] = field(default_factory=dict)


class ReferenceHierarchy:
    """Root aggregate over one standard edition; no orphan nodes allowed."""

    def __init__(
        self,
        standard_id: str,
        edition: str,
        nodes: tuple[ReferenceNode, ...],
    ) -> None:
        self._standard_id = standard_id
        self._edition = edition
        self._nodes: dict[RegulatoryId, ReferenceNode] = {}
        for node in nodes:
            if node.node_id in self._nodes:
                raise ValueError(f"Node duplicate {node.node_id}")
            self._nodes[node.node_id] = node
        self._validate_no_orphans()

    @property
    def standard_id(self) -> str:
        return self._standard_id

    @property
    def edition(self) -> str:
        return self._edition

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    def all_nodes(self) -> tuple[ReferenceNode, ...]:
        return tuple(sorted(self._nodes.values(), key=_ref_code_key))

    def get_node(self, regulatory_id: str) -> ReferenceNode | None:
        return self._nodes.get(regulatory_id)

    def node(self, regulatory_id: str) -> ReferenceNode:
        if regulatory_id not in self._nodes:
            raise KeyError(regulatory_id)
        return self._nodes[regulatory_id]

    def classes(self) -> tuple[ReferenceNode, ...]:
        return tuple(node for node in self.all_nodes() if node.node_type is ReferenceNodeType.CLASS)

    def children_of(self, node_id: str) -> tuple[ReferenceNode, ...]:
        return tuple(node for node in self.all_nodes() if node.parent_node_id == node_id)

    def ancestors_of(self, node_id: str) -> tuple[ReferenceNode, ...]:
        chain: list[ReferenceNode] = []
        current = self._nodes.get(node_id)
        while current is not None and current.parent_node_id is not None:
            parent = self._nodes.get(current.parent_node_id)
            if parent is None:
                break
            chain.append(parent)
            current = parent
        return tuple(reversed(chain))

    def class_for(self, node_id: str) -> ReferenceNode:
        """Return the root CLASS node enclosing *node_id*."""
        current = self._nodes.get(node_id)
        if current is None:
            raise KeyError(node_id)
        if current.node_type is ReferenceNodeType.CLASS:
            return current
        ancestors = self.ancestors_of(node_id)
        for ancestor in ancestors:
            if ancestor.node_type is ReferenceNodeType.CLASS:
                return ancestor
        raise ValueError(f"No CLASS node found for {node_id}")

    def _validate_no_orphans(self) -> None:
        orphans = [
            node.node_id
            for node in self._nodes.values()
            if node.parent_node_id is not None and node.parent_node_id not in self._nodes
        ]
        if orphans:
            raise ValueError(f"Orphan nodes with dangling parent: {sorted(orphans)}")


def _ref_code_key(node: ReferenceNode) -> str:
    return f"{node.ref_code:>10}_{node.node_id}"


__all__ = ["ReferenceNode", "ReferenceHierarchy"]
