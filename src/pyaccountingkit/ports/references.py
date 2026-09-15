"""Accounting reference provider — the port towards regulatory charts (LOT-10).

The domain never reads filesystem paths nor dataset files: everything goes
through this port, implemented by the ``adapters/regulatory`` adapters
(DoD ``provider paths absent from domain``).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from pyaccountingkit.domain.references.capabilities import (
    ReferenceCapabilitySet,
)
from pyaccountingkit.domain.references.concepts import ConceptRegistry
from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy, ReferenceNode
from pyaccountingkit.domain.references.relations import ConstraintRegister
from pyaccountingkit.domain.references.snapshots import ReferenceSnapshot
from pyaccountingkit.domain.references.standards import StandardType


class AccountingReferenceProviderProtocol(Protocol):
    """Contract of any regulatory chart-of-accounts provider."""

    def get_node(self, standard: StandardType, code: str) -> ReferenceNode | None:
        """Return the node under *code* of *standard*, if present."""
        ...

    def list_nodes_by_standard(self, standard: StandardType) -> Sequence[ReferenceNode]:
        """Return every node of *standard* in deterministic order."""
        ...

    def get_hierarchy(self, standard: StandardType) -> ReferenceHierarchy:
        """Return the full grounded hierarchy of *standard* (no orphans)."""
        ...

    def get_snapshot(self, standard: StandardType, version: str) -> ReferenceSnapshot:
        """Return a sealed, replayable snapshot of *standard*."""
        ...

    def capabilities(self, standard: StandardType) -> ReferenceCapabilitySet:
        """Return the declared capabilities for *standard*."""
        ...

    def constraints(self, standard: StandardType) -> ConstraintRegister:
        """Return the negative constraints register of *standard*."""
        ...

    def concept_registry(self) -> ConceptRegistry:
        """Return the neutral concept registry (jurisdiction-free)."""
        ...


__all__ = ["AccountingReferenceProviderProtocol"]
