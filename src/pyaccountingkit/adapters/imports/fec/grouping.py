"""Deterministic FEC entry grouping strategy."""

from __future__ import annotations

from pyaccountingkit.domain.imports.normalized_record import (
    NormalizedEntryGroup,
    NormalizedImportRecord,
    group_normalized_records,
)


class FECGroupingStrategy:
    """Group by the normalized ``JournalCode:EcritureNum`` source entry key."""

    def group(
        self,
        records: tuple[NormalizedImportRecord, ...],
    ) -> tuple[NormalizedEntryGroup, ...]:
        return group_normalized_records(records)


__all__ = ["FECGroupingStrategy"]
