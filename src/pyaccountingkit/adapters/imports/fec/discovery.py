"""Source discovery helpers for reviewable FEC onboarding."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pyaccountingkit.domain.imports.normalized_record import NormalizedImportRecord


@dataclass(frozen=True, slots=True)
class FECDiscoveryReport:
    source_accounts: tuple[tuple[str, str], ...]
    source_journals: tuple[tuple[str, str], ...]
    auxiliary_codes: tuple[str, ...]
    currencies: tuple[str, ...]
    date_from: date | None
    date_to: date | None
    entry_count: int
    line_count: int


def discover_fec(records: tuple[NormalizedImportRecord, ...]) -> FECDiscoveryReport:
    accounts = {
        (record.source_account_code, record.metadata.get("fec.CompteLib", ""))
        for record in records
    }
    journals = {
        (record.source_journal_code or "", record.metadata.get("fec.JournalLib", ""))
        for record in records
    }
    auxiliaries = {record.auxiliary_code for record in records if record.auxiliary_code}
    currencies = {str(record.currency) for record in records}
    dates = [record.accounting_date for record in records]
    return FECDiscoveryReport(
        source_accounts=tuple(sorted(accounts)),
        source_journals=tuple(sorted(journals)),
        auxiliary_codes=tuple(sorted(auxiliaries)),
        currencies=tuple(sorted(currencies)),
        date_from=min(dates) if dates else None,
        date_to=max(dates) if dates else None,
        entry_count=len({record.source_entry_key for record in records}),
        line_count=len(records),
    )


__all__ = ["FECDiscoveryReport", "discover_fec"]
