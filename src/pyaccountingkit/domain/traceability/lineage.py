"""Lineage — directed relationships between facts, queryable both ways."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class LineageEdge:
    """A directed relationship: ``from_entity`` produced ``to_entity``."""

    relation: str
    from_entity: str
    to_entity: str
    recorded_at: datetime

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (
            self.relation,
            self.from_entity,
            self.to_entity,
            self.recorded_at.isoformat(),
        )


class LineageQuery:
    """Append-only lineage store with forwards/backwards traversal."""

    def __init__(self) -> None:
        self._edges: list[LineageEdge] = []

    def record(self, edge: LineageEdge) -> None:
        self._edges.append(edge)

    def descendants(self, entity: str) -> tuple[LineageEdge, ...]:
        """Outgoing edges whose tail is *entity*."""
        return tuple(edge for edge in self._edges if edge.from_entity == entity)

    def ancestors(self, entity: str) -> tuple[LineageEdge, ...]:
        """Incoming edges whose head is *entity*."""
        return tuple(edge for edge in self._edges if edge.to_entity == entity)

    def edges_for(self, entity: str) -> tuple[LineageEdge, ...]:
        """Every edge mentioning *entity* in either direction."""
        return tuple(
            edge for edge in self._edges if edge.from_entity == entity or edge.to_entity == entity
        )


__all__ = ["LineageEdge", "LineageQuery"]
