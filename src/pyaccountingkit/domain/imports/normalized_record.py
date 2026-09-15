"""Source-neutral normalized accounting records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from types import MappingProxyType

from pyaccountingkit.core.currency import Currency


@dataclass(frozen=True, slots=True, order=True)
class SourceEntryKey:
    """Stable source-local key used to reconstruct an accounting entry."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("source entry key must not be empty")


@dataclass(frozen=True, slots=True)
class NormalizedImportRecord:
    """Generic accounting vocabulary independent of the source adapter."""

    batch_id: str
    normalized_record_id: str
    source_record_ref: str
    source_entry_key: SourceEntryKey
    source_account_code: str
    accounting_date: date
    debit: Decimal
    credit: Decimal
    currency: Currency
    source_line_key: str | None = None
    source_journal_code: str | None = None
    document_date: date | None = None
    description: str | None = None
    auxiliary_code: str | None = None
    dimensions: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = (
            "batch_id",
            "normalized_record_id",
            "source_record_ref",
            "source_account_code",
        )
        for name in required:
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be empty")
        if not isinstance(self.debit, Decimal) or not isinstance(self.credit, Decimal):
            raise TypeError("normalized debit and credit must be Decimal")
        if self.debit < 0 or self.credit < 0:
            raise ValueError("normalized debit and credit must be non-negative")
        if self.debit > 0 and self.credit > 0:
            raise ValueError("a normalized line cannot be both debit and credit")
        if self.debit == 0 and self.credit == 0:
            raise ValueError("a normalized line cannot be zero on both sides")
        object.__setattr__(self, "dimensions", MappingProxyType(dict(self.dimensions)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class NormalizedEntryGroup:
    """Deterministically grouped records belonging to one source entry."""

    source_entry_key: SourceEntryKey
    records: tuple[NormalizedImportRecord, ...]

    def __post_init__(self) -> None:
        if not self.records:
            raise ValueError("normalized entry group must contain records")
        if any(record.source_entry_key != self.source_entry_key for record in self.records):
            raise ValueError("all records must share the group source entry key")
        if len({record.accounting_date for record in self.records}) != 1:
            raise ValueError("all records in an entry group must share accounting_date")
        journals = {record.source_journal_code for record in self.records}
        if len(journals) != 1:
            raise ValueError("all records in an entry group must share source journal")

    @property
    def accounting_date(self) -> date:
        return self.records[0].accounting_date

    @property
    def source_journal_code(self) -> str | None:
        return self.records[0].source_journal_code

    @property
    def balanced(self) -> bool:
        return sum((r.debit for r in self.records), Decimal(0)) == sum(
            (r.credit for r in self.records), Decimal(0)
        )


def group_normalized_records(
    records: tuple[NormalizedImportRecord, ...],
) -> tuple[NormalizedEntryGroup, ...]:
    """Group deterministically by source entry key without dropping records."""
    buckets: dict[SourceEntryKey, list[NormalizedImportRecord]] = {}
    for record in records:
        buckets.setdefault(record.source_entry_key, []).append(record)
    return tuple(
        NormalizedEntryGroup(key, tuple(sorted(group, key=lambda r: r.normalized_record_id)))
        for key, group in sorted(buckets.items(), key=lambda item: item[0].value)
    )


__all__ = [
    "NormalizedEntryGroup",
    "NormalizedImportRecord",
    "SourceEntryKey",
    "group_normalized_records",
]
