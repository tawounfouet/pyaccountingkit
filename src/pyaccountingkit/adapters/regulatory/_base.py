"""Shared loading and provider behaviour for regulatory adapters (LOT-10).

Private module: not part of the public surface.  Hierarchy is consumed
from the *explicit* dataset fields; parent relations are never inferred.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pyaccountingkit.core.clock import ClockProtocol, SystemClock
from pyaccountingkit.domain.references.capabilities import (
    DEFAULT_FULL_CAPABILITIES,
    ReferenceCapabilitySet,
)
from pyaccountingkit.domain.references.concepts import (
    ConceptRegistry,
    ReferenceConcept,
    seed_neutral_concepts,
)
from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy, ReferenceNode
from pyaccountingkit.domain.references.relations import ConstraintRegister, NegativeConstraint
from pyaccountingkit.domain.references.snapshots import ReferenceSnapshot
from pyaccountingkit.domain.references.standards import ReferenceNodeType, StandardType

STANDARD_FILENAMES: Mapping[StandardType, str] = {
    StandardType.PCG_FRANCE: "pcg_2026_v1_structure.json",
    StandardType.SYSCOHADA: "syscohada_2017_v1_structure.json",
}


def parse_structure(doc: Mapping[str, Any]) -> ReferenceHierarchy:
    """Build a grounded hierarchy from the canonical ``nodes`` dataset shape."""
    nodes = tuple(_parse_node(raw) for raw in doc["nodes"])
    if not nodes:
        raise ValueError("Empty structure dataset")
    return ReferenceHierarchy(nodes[0].standard_id, nodes[0].edition, nodes)


def parse_concepts(doc: Mapping[str, Any]) -> ConceptRegistry:
    """Build a concept registry from the canonical ``concepts`` dataset shape."""
    registry = seed_neutral_concepts()
    for raw in doc["concepts"]:
        registry.add_concept(
            ReferenceConcept(
                code=str(raw["concept_id"]),
                label=str(raw["label"]),
                definition=str(raw.get("definition", "")),
            )
        )
    return registry


def _parse_node(raw: Mapping[str, Any]) -> ReferenceNode:
    raw_class = raw.get("account_class")
    return ReferenceNode(
        node_id=str(raw["node_id"]),
        node_type=ReferenceNodeType(str(raw["node_type"])),
        standard_id=str(raw["standard_id"]),
        edition=str(raw["edition"]),
        ref_code=str(raw["ref_code"]),
        label=str(raw["label_source"]),
        account_class=int(raw_class) if raw_class is not None else None,
        parent_node_id=(raw.get("parent_node_id") or None),
        is_leaf=bool(raw.get("is_leaf", False)),
        attributes=dict(raw.get("attributes") or {}),
    )


class _ReferenceProviderBase:
    """Lazy, deterministic provider logic shared by the adapters."""

    def __init__(
        self,
        clock: ClockProtocol | None = None,
        extra_constraints: Mapping[StandardType, tuple[NegativeConstraint, ...]] | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self._extra_constraints = extra_constraints or {}
        self._hierarchies: dict[StandardType, ReferenceHierarchy] = {}
        self._registers: dict[StandardType, ConstraintRegister] = {}
        self._concepts: ConceptRegistry = seed_neutral_concepts()

    def get_node(self, standard: StandardType, code: str) -> ReferenceNode | None:
        hierarchy = self.get_hierarchy(standard)
        node = hierarchy.get_node(code)
        if node is not None:
            return node
        matches = [n for n in hierarchy.all_nodes() if n.ref_code == code]
        return matches[0] if len(matches) == 1 else None

    def list_nodes_by_standard(self, standard: StandardType) -> Sequence[ReferenceNode]:
        return self.get_hierarchy(standard).all_nodes()

    def get_hierarchy(self, standard: StandardType) -> ReferenceHierarchy:
        if standard not in self._hierarchies:
            self._hierarchies[standard] = self._load_hierarchy(standard)
        return self._hierarchies[standard]

    def get_snapshot(self, standard: StandardType, version: str) -> ReferenceSnapshot:
        hierarchy = self.get_hierarchy(standard)
        return ReferenceSnapshot.seal(hierarchy, version, self._clock.now())

    def capabilities(self, standard: StandardType) -> ReferenceCapabilitySet:
        try:
            self.get_hierarchy(standard)
        except (KeyError, FileNotFoundError):
            return ReferenceCapabilitySet()
        return DEFAULT_FULL_CAPABILITIES

    def constraints(self, standard: StandardType) -> ConstraintRegister:
        if standard not in self._registers:
            register = ConstraintRegister(standard.canonical_id)
            for constraint in self._extra_constraints.get(standard, ()):
                register.add(constraint)
            self._registers[standard] = register
        return self._registers[standard]

    def concept_registry(self) -> ConceptRegistry:
        return self._concepts

    def _load_hierarchy(self, standard: StandardType) -> ReferenceHierarchy:
        raise NotImplementedError


__all__ = ["STANDARD_FILENAMES", "parse_structure", "parse_concepts", "_ReferenceProviderBase"]
