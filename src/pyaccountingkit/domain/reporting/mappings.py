"""Versioned account-to-statement mapping model."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.reporting.balance_line import AccountBalanceLine
from pyaccountingkit.domain.reporting.errors import StatementMappingError


class StatementMappingSetStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class StatementMappingStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class MappingProvenance(StrEnum):
    MANUAL = "MANUAL"
    REFERENCE_HINT = "REFERENCE_HINT"
    RULE_BASED = "RULE_BASED"
    MIGRATION = "MIGRATION"
    IMPORTED = "IMPORTED"
    VALIDATED_CANDIDATE = "VALIDATED_CANDIDATE"


class MappingBalanceSide(StrEnum):
    ANY = "ANY"
    DEBIT_SIDE = "DEBIT_SIDE"
    CREDIT_SIDE = "CREDIT_SIDE"


@dataclass(frozen=True, slots=True)
class StatementAccountMapping:
    """Explicit presentation mapping from one company account to one statement line."""

    mapping_id: str
    company_account_id: str
    statement_line_code: str
    allocation: Decimal
    mapping_status: StatementMappingStatus
    provenance: MappingProvenance
    effective_from: date
    effective_to: date | None = None
    balance_side: MappingBalanceSide = MappingBalanceSide.ANY

    def __post_init__(self) -> None:
        if not self.mapping_id.strip():
            raise StatementMappingError("statement mapping id must not be empty")
        if not self.company_account_id.strip():
            raise StatementMappingError("company account id must not be empty")
        if not self.statement_line_code.strip():
            raise StatementMappingError("statement line code must not be empty")
        if not isinstance(self.allocation, Decimal):
            raise StatementMappingError("mapping allocation must be a Decimal")
        if self.allocation <= 0 or self.allocation > Decimal("1"):
            raise StatementMappingError("mapping allocation must be in the interval (0, 1]")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise StatementMappingError("mapping effective_to cannot precede effective_from")
        if (
            self.provenance is MappingProvenance.REFERENCE_HINT
            and self.mapping_status is StatementMappingStatus.VALIDATED
        ):
            raise StatementMappingError(
                "REFERENCE_HINT provenance cannot become executable without explicit validation"
            )

    def effective_on(self, value: date) -> bool:
        if value < self.effective_from:
            return False
        return self.effective_to is None or value <= self.effective_to

    def applies_to(self, line: AccountBalanceLine, *, as_of: date) -> bool:
        if (
            line.company_account_identity != self.company_account_id
            or not self.effective_on(as_of)
        ):
            return False
        if self.balance_side is MappingBalanceSide.ANY:
            return True
        if self.balance_side is MappingBalanceSide.DEBIT_SIDE:
            return line.is_debit_balance
        if self.balance_side is MappingBalanceSide.CREDIT_SIDE:
            return line.is_credit_balance
        return False


@dataclass(frozen=True, slots=True)
class StatementMappingSet:
    """Versioned mapping set scoped to one AccountingEntity and definition."""

    mapping_set_id: str
    accounting_entity_id: EntityId
    statement_definition_id: str
    version: str
    status: StatementMappingSetStatus
    mappings: tuple[StatementAccountMapping, ...]
    effective_from: date
    effective_to: date | None = None

    def __post_init__(self) -> None:
        if not self.mapping_set_id.strip():
            raise StatementMappingError("statement mapping-set id must not be empty")
        if not str(self.accounting_entity_id).strip():
            raise StatementMappingError("statement mapping-set entity must not be empty")
        if not self.statement_definition_id.strip():
            raise StatementMappingError("statement definition id must not be empty")
        if not self.version.strip():
            raise StatementMappingError("mapping-set version must not be empty")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise StatementMappingError("mapping-set effective_to cannot precede effective_from")

        ids = [mapping.mapping_id for mapping in self.mappings]
        if len(ids) != len(set(ids)):
            raise StatementMappingError("statement mapping ids must be unique")

    @property
    def is_executable(self) -> bool:
        if self.status not in {
            StatementMappingSetStatus.VALIDATED,
            StatementMappingSetStatus.ACTIVE,
        }:
            return False
        return all(
            mapping.mapping_status is StatementMappingStatus.VALIDATED
            for mapping in self.mappings
        )

    def effective_on(self, value: date) -> bool:
        if value < self.effective_from:
            return False
        return self.effective_to is None or value <= self.effective_to

    @property
    def checksum(self) -> str:
        payload = {
            "mapping_set_id": self.mapping_set_id,
            "accounting_entity_id": str(self.accounting_entity_id),
            "statement_definition_id": self.statement_definition_id,
            "version": self.version,
            "status": self.status.value,
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "mappings": [
                {
                    "mapping_id": mapping.mapping_id,
                    "company_account_id": mapping.company_account_id,
                    "statement_line_code": mapping.statement_line_code,
                    "allocation": str(mapping.allocation),
                    "mapping_status": mapping.mapping_status.value,
                    "provenance": mapping.provenance.value,
                    "effective_from": mapping.effective_from.isoformat(),
                    "effective_to": (
                        mapping.effective_to.isoformat() if mapping.effective_to else None
                    ),
                    "balance_side": mapping.balance_side.value,
                }
                for mapping in sorted(self.mappings, key=lambda item: item.mapping_id)
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "MappingBalanceSide",
    "MappingProvenance",
    "StatementAccountMapping",
    "StatementMappingSet",
    "StatementMappingSetStatus",
    "StatementMappingStatus",
]
