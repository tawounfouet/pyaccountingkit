"""Accounting import batch aggregate and explicit lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

from pyaccountingkit.core.errors import InvalidImportTransitionError
from pyaccountingkit.core.identifiers import EntityId


class ImportBatchStatus(StrEnum):
    CREATED = "CREATED"
    ACQUIRED = "ACQUIRED"
    PARSED = "PARSED"
    NORMALIZED = "NORMALIZED"
    MAPPED = "MAPPED"
    VALIDATED = "VALIDATED"
    READY = "READY"
    IMPORTING = "IMPORTING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ImportMode(StrEnum):
    NORMAL_IMPORT = "NORMAL_IMPORT"
    TRUSTED_POSTED_HISTORY_IMPORT = "TRUSTED_POSTED_HISTORY_IMPORT"


class ImportTransactionMode(StrEnum):
    ALL_OR_NOTHING = "ALL_OR_NOTHING"
    PER_ITEM = "PER_ITEM"
    CHUNKED_ATOMIC = "CHUNKED_ATOMIC"


_ALLOWED: dict[ImportBatchStatus, frozenset[ImportBatchStatus]] = {
    ImportBatchStatus.CREATED: frozenset({ImportBatchStatus.ACQUIRED, ImportBatchStatus.CANCELLED}),
    ImportBatchStatus.ACQUIRED: frozenset(
        {ImportBatchStatus.PARSED, ImportBatchStatus.FAILED, ImportBatchStatus.CANCELLED}
    ),
    ImportBatchStatus.PARSED: frozenset(
        {ImportBatchStatus.NORMALIZED, ImportBatchStatus.FAILED, ImportBatchStatus.CANCELLED}
    ),
    ImportBatchStatus.NORMALIZED: frozenset(
        {ImportBatchStatus.MAPPED, ImportBatchStatus.FAILED, ImportBatchStatus.CANCELLED}
    ),
    ImportBatchStatus.MAPPED: frozenset(
        {ImportBatchStatus.VALIDATED, ImportBatchStatus.FAILED, ImportBatchStatus.CANCELLED}
    ),
    ImportBatchStatus.VALIDATED: frozenset(
        {ImportBatchStatus.READY, ImportBatchStatus.FAILED, ImportBatchStatus.CANCELLED}
    ),
    ImportBatchStatus.READY: frozenset({ImportBatchStatus.IMPORTING, ImportBatchStatus.CANCELLED}),
    ImportBatchStatus.IMPORTING: frozenset(
        {
            ImportBatchStatus.COMPLETED,
            ImportBatchStatus.COMPLETED_WITH_WARNINGS,
            ImportBatchStatus.FAILED,
        }
    ),
    ImportBatchStatus.COMPLETED: frozenset(),
    ImportBatchStatus.COMPLETED_WITH_WARNINGS: frozenset(),
    ImportBatchStatus.FAILED: frozenset(),
    ImportBatchStatus.CANCELLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class AccountingImportBatch:
    batch_id: str
    accounting_entity_id: EntityId
    source_type: str
    adapter_id: str
    adapter_version: str
    source_artifact_ref: str
    source_checksum: str
    correlation_id: str
    created_at: datetime
    import_mode: ImportMode = ImportMode.NORMAL_IMPORT
    transaction_mode: ImportTransactionMode = ImportTransactionMode.ALL_OR_NOTHING
    status: ImportBatchStatus = ImportBatchStatus.CREATED
    fiscal_year_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        required = (
            "batch_id",
            "source_type",
            "adapter_id",
            "adapter_version",
            "source_artifact_ref",
            "correlation_id",
        )
        for name in required:
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")

    def transition(
        self,
        target: ImportBatchStatus,
        *,
        at: datetime | None = None,
    ) -> AccountingImportBatch:
        if target not in _ALLOWED[self.status]:
            raise InvalidImportTransitionError(
                f"illegal import batch transition: {self.status} -> {target}"
            )
        started = self.started_at
        completed = self.completed_at
        if target is ImportBatchStatus.IMPORTING:
            if at is None:
                raise InvalidImportTransitionError("IMPORTING transition requires a timestamp")
            started = at
        terminal = {
            ImportBatchStatus.COMPLETED,
            ImportBatchStatus.COMPLETED_WITH_WARNINGS,
            ImportBatchStatus.FAILED,
        }
        if target in terminal:
            if at is None:
                raise InvalidImportTransitionError(f"{target} transition requires a timestamp")
            completed = at
        return replace(self, status=target, started_at=started, completed_at=completed)


__all__ = ["AccountingImportBatch", "ImportBatchStatus", "ImportMode", "ImportTransactionMode"]
