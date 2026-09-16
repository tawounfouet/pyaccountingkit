"""Versioned statement-line to regulatory-node mappings."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.reporting.errors import (
    NonExecutableRegulatoryMappingError,
    RegulatoryMappingError,
)


class RegulatoryMappingSetStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class RegulatoryMappingStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class RegulatoryMappingProvenance(StrEnum):
    MANUAL = "MANUAL"
    REFERENCE_HINT = "REFERENCE_HINT"
    RULE_BASED = "RULE_BASED"
    MIGRATION = "MIGRATION"
    IMPORTED = "IMPORTED"
    VALIDATED_CANDIDATE = "VALIDATED_CANDIDATE"


@dataclass(frozen=True, slots=True)
class RegulatoryStatementMapping:
    """Explicit mapping from one statement line to one regulatory node."""

    mapping_id: str
    statement_line_code: str
    reference_node_id: str
    allocation: Decimal
    status: RegulatoryMappingStatus
    provenance: RegulatoryMappingProvenance
    effective_from: date
    effective_to: date | None = None
    review_required: bool = False

    def __post_init__(self) -> None:
        if not self.mapping_id.strip():
            raise RegulatoryMappingError("regulatory mapping id must not be empty")
        if not self.statement_line_code.strip():
            raise RegulatoryMappingError("statement line code must not be empty")
        if not self.reference_node_id.strip():
            raise RegulatoryMappingError("reference node id must not be empty")
        if not isinstance(self.allocation, Decimal):
            raise RegulatoryMappingError("regulatory mapping allocation must be a Decimal")
        if self.allocation <= 0 or self.allocation > Decimal("1"):
            raise RegulatoryMappingError(
                "regulatory mapping allocation must be in the interval (0, 1]"
            )
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise RegulatoryMappingError("mapping effective_to cannot precede effective_from")
        if self.review_required and self.status is RegulatoryMappingStatus.VALIDATED:
            raise RegulatoryMappingError(
                "review-required regulatory mappings cannot be validated"
            )
        if (
            self.provenance is RegulatoryMappingProvenance.REFERENCE_HINT
            and self.status is RegulatoryMappingStatus.VALIDATED
        ):
            raise RegulatoryMappingError(
                "REFERENCE_HINT cannot become executable without explicit validation provenance"
            )

    @property
    def is_executable(self) -> bool:
        return self.status is RegulatoryMappingStatus.VALIDATED and not self.review_required

    def effective_on(self, value: date) -> bool:
        if value < self.effective_from:
            return False
        return self.effective_to is None or value <= self.effective_to


@dataclass(frozen=True, slots=True)
class RegulatoryMappingSet:
    """Entity-scoped, effective-dated mappings for one profile and reference model."""

    mapping_set_id: str
    accounting_entity_id: EntityId
    profile_id: str
    reference_model_id: str
    version: str
    status: RegulatoryMappingSetStatus
    mappings: tuple[RegulatoryStatementMapping, ...]
    effective_from: date
    effective_to: date | None = None

    def __post_init__(self) -> None:
        required = {
            "mapping_set_id": self.mapping_set_id,
            "profile_id": self.profile_id,
            "reference_model_id": self.reference_model_id,
            "version": self.version,
        }
        for name, value in required.items():
            if not value.strip():
                raise RegulatoryMappingError(f"{name} must not be empty")
        if not str(self.accounting_entity_id).strip():
            raise RegulatoryMappingError("regulatory mapping-set entity must not be empty")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise RegulatoryMappingError("mapping-set effective_to cannot precede effective_from")
        ids = [mapping.mapping_id for mapping in self.mappings]
        if len(ids) != len(set(ids)):
            raise RegulatoryMappingError("regulatory mapping ids must be unique")

    @property
    def is_executable(self) -> bool:
        if self.status not in {
            RegulatoryMappingSetStatus.VALIDATED,
            RegulatoryMappingSetStatus.ACTIVE,
        }:
            return False
        return all(mapping.is_executable for mapping in self.mappings)

    def effective_on(self, value: date) -> bool:
        if value < self.effective_from:
            return False
        return self.effective_to is None or value <= self.effective_to

    def executable_mappings_for(
        self,
        statement_line_code: str,
        *,
        as_of: date,
    ) -> tuple[RegulatoryStatementMapping, ...]:
        if not self.is_executable:
            raise NonExecutableRegulatoryMappingError(
                f"regulatory mapping set {self.mapping_set_id!r} is not executable"
            )
        if not self.effective_on(as_of):
            raise NonExecutableRegulatoryMappingError(
                f"regulatory mapping set {self.mapping_set_id!r} is not effective on "
                f"{as_of.isoformat()}"
            )
        return tuple(
            mapping
            for mapping in self.mappings
            if mapping.statement_line_code == statement_line_code
            and mapping.effective_on(as_of)
            and mapping.is_executable
        )

    def assert_allocations(self, *, as_of: date) -> None:
        """Ensure every mapped source line allocates exactly one at the execution date."""
        if not self.is_executable or not self.effective_on(as_of):
            raise NonExecutableRegulatoryMappingError(
                f"regulatory mapping set {self.mapping_set_id!r} is not executable"
            )
        source_codes = {
            mapping.statement_line_code
            for mapping in self.mappings
            if mapping.effective_on(as_of) and mapping.is_executable
        }
        for source_code in sorted(source_codes):
            total = sum(
                (
                    mapping.allocation
                    for mapping in self.mappings
                    if mapping.statement_line_code == source_code
                    and mapping.effective_on(as_of)
                    and mapping.is_executable
                ),
                Decimal("0"),
            )
            if total != Decimal("1"):
                raise RegulatoryMappingError(
                    f"regulatory mappings for statement line {source_code!r} must allocate "
                    f"exactly 1, got {total}"
                )

    @property
    def checksum(self) -> str:
        payload = {
            "mapping_set_id": self.mapping_set_id,
            "accounting_entity_id": str(self.accounting_entity_id),
            "profile_id": self.profile_id,
            "reference_model_id": self.reference_model_id,
            "version": self.version,
            "status": self.status.value,
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "mappings": [
                {
                    "mapping_id": mapping.mapping_id,
                    "statement_line_code": mapping.statement_line_code,
                    "reference_node_id": mapping.reference_node_id,
                    "allocation": str(mapping.allocation),
                    "status": mapping.status.value,
                    "provenance": mapping.provenance.value,
                    "review_required": mapping.review_required,
                    "effective_from": mapping.effective_from.isoformat(),
                    "effective_to": (
                        mapping.effective_to.isoformat() if mapping.effective_to else None
                    ),
                }
                for mapping in sorted(self.mappings, key=lambda item: item.mapping_id)
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "RegulatoryMappingProvenance",
    "RegulatoryMappingSet",
    "RegulatoryMappingSetStatus",
    "RegulatoryMappingStatus",
    "RegulatoryStatementMapping",
]
