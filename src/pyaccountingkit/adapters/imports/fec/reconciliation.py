"""Post-import reconciliation model for FEC migrations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pyaccountingkit.domain.imports.normalized_record import NormalizedImportRecord


@dataclass(frozen=True, slots=True)
class FECReconciliationReport:
    normalized_entry_count: int
    normalized_line_count: int
    normalized_debit: Decimal
    normalized_credit: Decimal
    imported_entry_count: int
    imported_line_count: int
    imported_debit: Decimal
    imported_credit: Decimal

    @property
    def source_balanced(self) -> bool:
        return self.normalized_debit == self.normalized_credit

    @property
    def imported_balanced(self) -> bool:
        return self.imported_debit == self.imported_credit

    @property
    def reconciled(self) -> bool:
        return (
            self.source_balanced
            and self.imported_balanced
            and self.normalized_entry_count == self.imported_entry_count
            and self.normalized_line_count == self.imported_line_count
            and self.normalized_debit == self.imported_debit
            and self.normalized_credit == self.imported_credit
        )


def build_fec_reconciliation_report(
    records: tuple[NormalizedImportRecord, ...],
    *,
    imported_entry_count: int,
    imported_line_count: int,
    imported_debit: Decimal,
    imported_credit: Decimal,
) -> FECReconciliationReport:
    return FECReconciliationReport(
        normalized_entry_count=len({record.source_entry_key for record in records}),
        normalized_line_count=len(records),
        normalized_debit=sum((record.debit for record in records), Decimal(0)),
        normalized_credit=sum((record.credit for record in records), Decimal(0)),
        imported_entry_count=imported_entry_count,
        imported_line_count=imported_line_count,
        imported_debit=imported_debit,
        imported_credit=imported_credit,
    )


__all__ = ["FECReconciliationReport", "build_fec_reconciliation_report"]
