"""Typed validation issues for generic accounting imports."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType

from pyaccountingkit.domain.imports.normalized_record import SourceEntryKey


class ImportIssueSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ImportRecordDisposition(StrEnum):
    ACCEPT = "ACCEPT"
    WARNING = "WARNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECT = "REJECT"
    QUARANTINE = "QUARANTINE"


@dataclass(frozen=True, slots=True)
class ImportIssue:
    issue_code: str
    severity: ImportIssueSeverity
    blocking: bool
    message: str
    source_record_refs: tuple[str, ...] = ()
    source_entry_key: SourceEntryKey | None = None
    expected: str | None = None
    actual: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.issue_code.strip() or not self.message.strip():
            raise ValueError("issue_code and message must not be empty")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class ImportValidationReport:
    batch_id: str
    issues: tuple[ImportIssue, ...]
    total_records: int
    accepted_records: int
    rejected_records: int
    warning_records: int
    unmapped_accounts: int
    unmapped_journals: int
    total_debit: Decimal
    total_credit: Decimal

    @property
    def valid(self) -> bool:
        return not any(issue.blocking for issue in self.issues)

    @property
    def difference(self) -> Decimal:
        return self.total_debit - self.total_credit


__all__ = [
    "ImportIssue",
    "ImportIssueSeverity",
    "ImportRecordDisposition",
    "ImportValidationReport",
]
