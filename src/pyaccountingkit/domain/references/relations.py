"""Negative constraints — first-class doctrine rules (LOT-10).

The register forbids specific behaviours (inverse balance, direct posting)
for given standard nodes, exactly as expressed by the doctrine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pyaccountingkit.domain.references.standards import RegulatoryId


class ConstraintKind(StrEnum):
    DEBIT_ONLY = "DEBIT_ONLY"
    CREDIT_ONLY = "CREDIT_ONLY"
    NO_DIRECT_POSTING = "NO_DIRECT_POSTING"


@dataclass(frozen=True, slots=True)
class NegativeConstraint:
    """A prohibition attached to one node of one standard."""

    node_id: RegulatoryId
    kind: ConstraintKind
    reason: str
    standard_id: str


class ConstraintRegister:
    """Per-standard registry of negative constraints."""

    def __init__(self, standard_id: str) -> None:
        self._standard_id = standard_id
        self._by_node: dict[RegulatoryId, tuple[NegativeConstraint, ...]] = {}

    @property
    def standard_id(self) -> str:
        return self._standard_id

    def add(self, constraint: NegativeConstraint) -> None:
        if constraint.standard_id != self._standard_id:
            raise ValueError(
                f"Constraint for {constraint.standard_id} in registry {self._standard_id}"
            )
        current = self._by_node.get(constraint.node_id, ())
        self._by_node[constraint.node_id] = current + (constraint,)

    def for_node(self, node_id: str) -> tuple[NegativeConstraint, ...]:
        return self._by_node.get(node_id, ())

    def balance_kind(self, node_id: str) -> ConstraintKind | None:
        for constraint in self._by_node.get(node_id, ()):
            if constraint.kind in (ConstraintKind.DEBIT_ONLY, ConstraintKind.CREDIT_ONLY):
                return constraint.kind
        return None

    def all(self) -> tuple[NegativeConstraint, ...]:
        return tuple(
            constraint for constraints in self._by_node.values() for constraint in constraints
        )


__all__ = ["ConstraintKind", "NegativeConstraint", "ConstraintRegister"]
