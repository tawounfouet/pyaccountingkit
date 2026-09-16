"""Canonical regulatory reporting models independent from provider datasets."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from pyaccountingkit.domain.reporting.errors import RegulatoryReportingError


class ReferenceReportingNodeType(StrEnum):
    DETAIL = "DETAIL"
    SUBTOTAL = "SUBTOTAL"
    TOTAL = "TOTAL"
    HEADER = "HEADER"
    DISCLOSURE = "DISCLOSURE"


class ReferenceReportingValueType(StrEnum):
    MONEY = "MONEY"
    TEXT = "TEXT"


@dataclass(frozen=True, slots=True)
class ReferenceReportingNode:
    """One official reporting node plus non-executable source hint metadata."""

    node_id: str
    code: str
    label: str
    node_type: ReferenceReportingNodeType
    order: int
    parent_node_id: str | None = None
    required: bool = False
    value_type: ReferenceReportingValueType = ReferenceReportingValueType.MONEY
    human_validation_required: bool = False
    account_hints_executable: bool = False
    account_hints: tuple[str, ...] = ()
    provenance: str | None = None

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise RegulatoryReportingError("reference reporting node id must not be empty")
        if not self.code.strip():
            raise RegulatoryReportingError("reference reporting node code must not be empty")
        if not self.label.strip() and self.node_type is not ReferenceReportingNodeType.HEADER:
            raise RegulatoryReportingError(
                f"reference reporting node {self.code!r} must have a label"
            )
        if self.order < 0:
            raise RegulatoryReportingError(
                f"reference reporting node {self.code!r} order must be >= 0"
            )
        if len(self.account_hints) != len(set(self.account_hints)):
            raise RegulatoryReportingError(
                f"reference reporting node {self.code!r} account hints must be unique"
            )
        if any(not hint.strip() for hint in self.account_hints):
            raise RegulatoryReportingError("account hints must not contain empty values")
        if self.human_validation_required and self.account_hints_executable:
            raise RegulatoryReportingError(
                "human-validation-required account hints cannot be executable"
            )


@dataclass(frozen=True, slots=True)
class ReferenceReportingModel:
    """Sealed official reporting structure pinned to one reference snapshot."""

    model_id: str
    model_code: str
    framework: str
    edition: str
    reference_snapshot_id: str
    reference_snapshot_checksum: str
    nodes: tuple[ReferenceReportingNode, ...]

    def __post_init__(self) -> None:
        required = {
            "model_id": self.model_id,
            "model_code": self.model_code,
            "framework": self.framework,
            "edition": self.edition,
            "reference_snapshot_id": self.reference_snapshot_id,
            "reference_snapshot_checksum": self.reference_snapshot_checksum,
        }
        for name, value in required.items():
            if not value.strip():
                raise RegulatoryReportingError(f"{name} must not be empty")
        if not self.nodes:
            raise RegulatoryReportingError("reference reporting model requires at least one node")

        ids = [node.node_id for node in self.nodes]
        codes = [node.code for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise RegulatoryReportingError("reference reporting node ids must be unique")
        if len(codes) != len(set(codes)):
            raise RegulatoryReportingError("reference reporting node codes must be unique")

        known_ids = set(ids)
        by_id = {node.node_id: node for node in self.nodes}
        for node in self.nodes:
            if node.parent_node_id is not None and node.parent_node_id not in known_ids:
                raise RegulatoryReportingError(
                    f"reference reporting node {node.code!r} has unknown parent "
                    f"{node.parent_node_id!r}"
                )
            seen: set[str] = set()
            current = node
            while current.parent_node_id is not None:
                if current.node_id in seen:
                    raise RegulatoryReportingError(
                        f"reference reporting hierarchy cycle detected at {current.code!r}"
                    )
                seen.add(current.node_id)
                current = by_id[current.parent_node_id]

    @property
    def ordered_nodes(self) -> tuple[ReferenceReportingNode, ...]:
        return tuple(sorted(self.nodes, key=lambda node: (node.order, node.code)))

    def node_by_id(self, node_id: str) -> ReferenceReportingNode:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        raise KeyError(node_id)

    def node_by_code(self, code: str) -> ReferenceReportingNode:
        for node in self.nodes:
            if node.code == code:
                return node
        raise KeyError(code)

    @property
    def checksum(self) -> str:
        payload = {
            "model_id": self.model_id,
            "model_code": self.model_code,
            "framework": self.framework,
            "edition": self.edition,
            "reference_snapshot_id": self.reference_snapshot_id,
            "reference_snapshot_checksum": self.reference_snapshot_checksum,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "code": node.code,
                    "label": node.label,
                    "node_type": node.node_type.value,
                    "order": node.order,
                    "parent_node_id": node.parent_node_id,
                    "required": node.required,
                    "value_type": node.value_type.value,
                    "human_validation_required": node.human_validation_required,
                    "account_hints_executable": node.account_hints_executable,
                    "account_hints": list(node.account_hints),
                    "provenance": node.provenance,
                }
                for node in self.ordered_nodes
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "ReferenceReportingModel",
    "ReferenceReportingNode",
    "ReferenceReportingNodeType",
    "ReferenceReportingValueType",
]
