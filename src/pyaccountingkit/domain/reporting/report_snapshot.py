"""Immutable financial-report snapshots for publication and replay."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.engine import FinancialStatementResult
from pyaccountingkit.domain.reporting.statement_definition import FinancialStatementType


class ReportSnapshotStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"


class ReportSnapshotFreshness(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"


@dataclass(frozen=True, slots=True)
class ReportSnapshotLine:
    code: str
    label: str
    amount: Money
    comparative_amount: Money | None = None


@dataclass(frozen=True, slots=True)
class ReportSnapshot:
    """Sealed report projection pinning every replay-relevant coordinate."""

    snapshot_id: str
    accounting_entity_id: EntityId
    report_type: FinancialStatementType
    source_period_id: str
    source_checksum: str
    statement_definition_id: str
    statement_definition_version: str
    statement_definition_checksum: str
    mapping_set_id: str
    mapping_set_version: str
    mapping_set_checksum: str
    result_checksum: str
    created_at: datetime
    status: ReportSnapshotStatus
    lines: tuple[ReportSnapshotLine, ...]
    checksum: str

    @classmethod
    def from_result(
        cls,
        *,
        snapshot_id: str,
        result: FinancialStatementResult,
        created_at: datetime,
        status: ReportSnapshotStatus = ReportSnapshotStatus.PUBLISHED,
    ) -> ReportSnapshot:
        if not snapshot_id.strip():
            raise ValueError("report snapshot id must not be empty")
        lines = tuple(
            ReportSnapshotLine(
                code=line.code,
                label=line.label,
                amount=line.amount,
                comparative_amount=line.comparative_amount,
            )
            for line in result.lines
        )
        checksum = cls._checksum(result=result, status=status, lines=lines)
        return cls(
            snapshot_id=snapshot_id,
            accounting_entity_id=result.accounting_entity_id,
            report_type=result.statement_type,
            source_period_id=result.source_period_id,
            source_checksum=result.source_checksum,
            statement_definition_id=result.statement_definition_id,
            statement_definition_version=result.statement_definition_version,
            statement_definition_checksum=result.statement_definition_checksum,
            mapping_set_id=result.mapping_set_id,
            mapping_set_version=result.mapping_set_version,
            mapping_set_checksum=result.mapping_set_checksum,
            result_checksum=result.checksum,
            created_at=created_at,
            status=status,
            lines=lines,
            checksum=checksum,
        )

    def freshness_against(self, source_checksum: str) -> ReportSnapshotFreshness:
        return (
            ReportSnapshotFreshness.CURRENT
            if source_checksum == self.source_checksum
            else ReportSnapshotFreshness.STALE
        )

    @staticmethod
    def _checksum(
        *,
        result: FinancialStatementResult,
        status: ReportSnapshotStatus,
        lines: tuple[ReportSnapshotLine, ...],
    ) -> str:
        payload = {
            "accounting_entity_id": str(result.accounting_entity_id),
            "report_type": result.statement_type.value,
            "source_period_id": result.source_period_id,
            "source_checksum": result.source_checksum,
            "statement_definition_id": result.statement_definition_id,
            "statement_definition_version": result.statement_definition_version,
            "statement_definition_checksum": result.statement_definition_checksum,
            "mapping_set_id": result.mapping_set_id,
            "mapping_set_version": result.mapping_set_version,
            "mapping_set_checksum": result.mapping_set_checksum,
            "result_checksum": result.checksum,
            "status": status.value,
            "lines": [
                {
                    "code": line.code,
                    "amount": str(line.amount.amount),
                    "currency": str(line.amount.currency.code),
                    "comparative": (
                        str(line.comparative_amount.amount)
                        if line.comparative_amount is not None
                        else None
                    ),
                }
                for line in lines
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "ReportSnapshot",
    "ReportSnapshotFreshness",
    "ReportSnapshotLine",
    "ReportSnapshotStatus",
]
