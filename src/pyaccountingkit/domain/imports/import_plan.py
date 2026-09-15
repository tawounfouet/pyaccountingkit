"""Deterministic, reviewable accounting import plans."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from pyaccountingkit.core.errors import InvalidImportPlanError, StaleImportPlanError
from pyaccountingkit.core.identifiers import AccountId, EntityId, JournalId, PeriodId
from pyaccountingkit.domain.imports.normalized_record import SourceEntryKey


@dataclass(frozen=True, slots=True)
class ImportPlannedLine:
    source_record_ref: str
    account_id: AccountId
    debit: Decimal
    credit: Decimal


@dataclass(frozen=True, slots=True)
class ImportEntryPlan:
    source_entry_key: SourceEntryKey
    accounting_date: date
    journal_id: JournalId
    period_id: PeriodId
    lines: tuple[ImportPlannedLine, ...]
    description: str | None = None

    def __post_init__(self) -> None:
        if len(self.lines) < 2:
            raise InvalidImportPlanError("an import entry plan requires at least two lines")
        debit = sum((line.debit for line in self.lines), Decimal(0))
        credit = sum((line.credit for line in self.lines), Decimal(0))
        if debit != credit:
            raise InvalidImportPlanError("an import entry plan must be balanced")


@dataclass(frozen=True, slots=True)
class ImportPlan:
    batch_id: str
    entity_id: EntityId
    source_checksum: str
    adapter_id: str
    adapter_version: str
    mapping_version: str
    chart_version: str
    entry_plans: tuple[ImportEntryPlan, ...]
    expected_line_count: int
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        planned_lines = sum(len(entry.lines) for entry in self.entry_plans)
        if self.expected_line_count != planned_lines:
            raise InvalidImportPlanError("expected_line_count does not match planned lines")
        keys = [entry.source_entry_key for entry in self.entry_plans]
        if len(keys) != len(set(keys)):
            raise InvalidImportPlanError("source entry keys must be unique within an import plan")

    @property
    def expected_entry_count(self) -> int:
        return len(self.entry_plans)

    @property
    def checksum(self) -> str:
        payload = {
            "batch_id": self.batch_id,
            "entity_id": str(self.entity_id),
            "source_checksum": self.source_checksum,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "mapping_version": self.mapping_version,
            "chart_version": self.chart_version,
            "entries": [
                {
                    "key": entry.source_entry_key.value,
                    "date": entry.accounting_date.isoformat(),
                    "journal": str(entry.journal_id),
                    "period": str(entry.period_id),
                    "description": entry.description,
                    "lines": [
                        {
                            "source": line.source_record_ref,
                            "account": str(line.account_id),
                            "debit": str(line.debit),
                            "credit": str(line.credit),
                        }
                        for line in entry.lines
                    ],
                }
                for entry in self.entry_plans
            ],
            "warnings": list(self.warnings),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def assert_fresh(
        self,
        *,
        source_checksum: str,
        adapter_version: str,
        mapping_version: str,
        chart_version: str,
    ) -> None:
        current = (source_checksum, adapter_version, mapping_version, chart_version)
        planned = (
            self.source_checksum,
            self.adapter_version,
            self.mapping_version,
            self.chart_version,
        )
        if current != planned:
            raise StaleImportPlanError(
                "stale import plan: source or resolution versions changed"
            )


@dataclass(frozen=True, slots=True)
class ImportCheckpoint:
    batch_id: str
    plan_checksum: str
    imported_count: int
    last_source_entry_key: SourceEntryKey | None = None
    last_chunk_id: str | None = None

    def __post_init__(self) -> None:
        if self.imported_count < 0:
            raise InvalidImportPlanError("imported_count must be non-negative")


__all__ = ["ImportCheckpoint", "ImportEntryPlan", "ImportPlan", "ImportPlannedLine"]
