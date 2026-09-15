"""Reference snapshots — sealed, replayable captures of a standard (LOT-10)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pyaccountingkit.domain.references.hierarchy import ReferenceHierarchy, ReferenceNode
from pyaccountingkit.domain.traceability.trace import CanonicalHasher


@dataclass(frozen=True, slots=True)
class ReferenceSnapshot:
    """Immutable, checksummed capture of one standard edition."""

    standard_id: str
    edition: str
    version: str
    checksum: str
    captured_at: datetime
    nodes: tuple[ReferenceNode, ...]

    @classmethod
    def seal(
        cls,
        hierarchy: ReferenceHierarchy,
        version: str,
        captured_at: datetime,
    ) -> ReferenceSnapshot:
        nodes = tuple(sorted(hierarchy.all_nodes(), key=lambda node: node.node_id))
        checksum = cls._digest(
            standard_id=hierarchy.standard_id,
            edition=hierarchy.edition,
            version=version,
            nodes=nodes,
        )
        return cls(
            standard_id=hierarchy.standard_id,
            edition=hierarchy.edition,
            version=version,
            checksum=checksum,
            captured_at=captured_at,
            nodes=nodes,
        )

    def replay(self) -> ReferenceHierarchy:
        """Deterministically rebuild the source hierarchy from the snapshot."""
        return ReferenceHierarchy(
            standard_id=self.standard_id,
            edition=self.edition,
            nodes=self.nodes,
        )

    def verify(self) -> bool:
        """Recompute the checksum; `captured_at` is intentionally excluded."""
        digest = self._digest(self.standard_id, self.edition, self.version, self.nodes)
        return digest == self.checksum

    @staticmethod
    def _digest(
        standard_id: str,
        edition: str,
        version: str,
        nodes: tuple[ReferenceNode, ...],
    ) -> str:
        payload: dict[str, Any] = {
            "standard_id": standard_id,
            "edition": edition,
            "version": version,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "node_type": node.node_type.value,
                    "ref_code": node.ref_code,
                    "label": node.label,
                    "account_class": node.account_class,
                    "parent_node_id": node.parent_node_id,
                    "is_leaf": node.is_leaf,
                    "attributes": sorted(
                        (key, _stringify(value)) for key, value in node.attributes.items()
                    ),
                }
                for node in nodes
            ],
        }
        return CanonicalHasher.digest(payload)


def _stringify(value: object) -> str:
    if value is None:
        return "null"
    return str(value)


__all__ = ["ReferenceSnapshot"]
