"""Versioned regulatory-reporting profiles for deterministic execution."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.reporting.errors import (
    RegulatoryProfileError,
    RegulatoryProfileNotActiveError,
    RegulatoryProfileNotEffectiveError,
    RegulatoryReferenceMismatchError,
)


class RegulatoryProfileStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True, slots=True)
class RegulatoryReportingProfile:
    """Immutable profile pinning the exact regulatory reference coordinates."""

    profile_id: str
    code: str
    framework: str
    jurisdiction: str
    edition: str
    version: str
    status: RegulatoryProfileStatus
    reference_snapshot_id: str
    reference_snapshot_checksum: str
    financial_statement_definition_ids: tuple[str, ...]
    regulatory_mapping_set_id: str
    export_definition_ids: tuple[str, ...]
    effective_from: date
    effective_to: date | None = None
    accounting_entity_id: EntityId | None = None

    def __post_init__(self) -> None:
        required = {
            "profile_id": self.profile_id,
            "code": self.code,
            "framework": self.framework,
            "jurisdiction": self.jurisdiction,
            "edition": self.edition,
            "version": self.version,
            "reference_snapshot_id": self.reference_snapshot_id,
            "reference_snapshot_checksum": self.reference_snapshot_checksum,
            "regulatory_mapping_set_id": self.regulatory_mapping_set_id,
        }
        for name, value in required.items():
            if not value.strip():
                raise RegulatoryProfileError(f"{name} must not be empty")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise RegulatoryProfileError("profile effective_to cannot precede effective_from")
        if not self.financial_statement_definition_ids:
            raise RegulatoryProfileError(
                "regulatory profile requires at least one financial statement definition"
            )
        if len(self.financial_statement_definition_ids) != len(
            set(self.financial_statement_definition_ids)
        ):
            raise RegulatoryProfileError("financial statement definition ids must be unique")
        if len(self.export_definition_ids) != len(set(self.export_definition_ids)):
            raise RegulatoryProfileError("export definition ids must be unique")
        if any(not value.strip() for value in self.financial_statement_definition_ids):
            raise RegulatoryProfileError("financial statement definition ids must not be empty")
        if any(not value.strip() for value in self.export_definition_ids):
            raise RegulatoryProfileError("export definition ids must not be empty")

    @property
    def is_executable(self) -> bool:
        return self.status is RegulatoryProfileStatus.ACTIVE

    def effective_on(self, value: date) -> bool:
        if value < self.effective_from:
            return False
        return self.effective_to is None or value <= self.effective_to

    def assert_executable(
        self,
        *,
        entity_id: EntityId,
        as_of: date,
        reference_snapshot_id: str,
        reference_snapshot_checksum: str,
    ) -> None:
        if not self.is_executable:
            raise RegulatoryProfileNotActiveError(
                f"regulatory profile {self.profile_id!r} is not active"
            )
        if not self.effective_on(as_of):
            raise RegulatoryProfileNotEffectiveError(
                f"regulatory profile {self.profile_id!r} is not effective on {as_of.isoformat()}"
            )
        if self.accounting_entity_id is not None:
            require_same_entity(
                self.accounting_entity_id,
                entity_id,
                resource="regulatory reporting profile",
            )
        if (
            reference_snapshot_id != self.reference_snapshot_id
            or reference_snapshot_checksum != self.reference_snapshot_checksum
        ):
            raise RegulatoryReferenceMismatchError(
                "regulatory profile reference snapshot does not match execution coordinates"
            )

    @property
    def checksum(self) -> str:
        payload = {
            "profile_id": self.profile_id,
            "accounting_entity_id": (
                str(self.accounting_entity_id) if self.accounting_entity_id is not None else None
            ),
            "code": self.code,
            "framework": self.framework,
            "jurisdiction": self.jurisdiction,
            "edition": self.edition,
            "version": self.version,
            "status": self.status.value,
            "reference_snapshot_id": self.reference_snapshot_id,
            "reference_snapshot_checksum": self.reference_snapshot_checksum,
            "financial_statement_definition_ids": sorted(self.financial_statement_definition_ids),
            "regulatory_mapping_set_id": self.regulatory_mapping_set_id,
            "export_definition_ids": sorted(self.export_definition_ids),
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


__all__ = ["RegulatoryProfileStatus", "RegulatoryReportingProfile"]
