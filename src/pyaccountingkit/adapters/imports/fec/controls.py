"""FEC-specific validation controls kept outside the generic import domain."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from pyaccountingkit.core.currency import lookup_currency
from pyaccountingkit.domain.imports.issues import (
    ImportIssue,
    ImportIssueSeverity,
    ImportValidationReport,
)
from pyaccountingkit.domain.imports.normalized_record import NormalizedImportRecord
from pyaccountingkit.domain.imports.raw_record import RawImportRecord

from .schema import FECSourceDescriptor


class FECValidator:
    """Validate structural/accounting FEC constraints without mutating records."""

    def __init__(self, descriptor: FECSourceDescriptor | None = None) -> None:
        self.descriptor = descriptor or FECSourceDescriptor()

    def validate_raw(self, records: tuple[RawImportRecord, ...]) -> tuple[ImportIssue, ...]:
        issues: list[ImportIssue] = []
        for raw in records:
            fields = raw.raw_fields
            for name, code in (
                ("JournalCode", "FEC_MISSING_JOURNAL_CODE"),
                ("EcritureNum", "FEC_MISSING_ENTRY_NUMBER"),
                ("CompteNum", "FEC_MISSING_ACCOUNT_NUMBER"),
                ("EcritureDate", "FEC_MISSING_ENTRY_DATE"),
            ):
                if not (fields.get(name) or "").strip():
                    issues.append(self._issue(code, raw, f"missing required FEC value {name}"))

            entry_date = self._raw_date(fields.get("EcritureDate"))
            if (fields.get("EcritureDate") or "").strip() and entry_date is None:
                issues.append(self._issue("FEC_INVALID_ENTRY_DATE", raw, "invalid EcritureDate"))
            elif entry_date is not None and not self._date_in_fiscal_year(entry_date):
                issues.append(
                    self._issue(
                        "FEC_DATE_OUTSIDE_FISCAL_YEAR",
                        raw,
                        "EcritureDate is outside configured fiscal year",
                    )
                )

            debit = self._raw_decimal(fields.get("Debit"))
            credit = self._raw_decimal(fields.get("Credit"))
            if debit is None:
                issues.append(self._issue("FEC_INVALID_DEBIT", raw, "invalid Debit"))
            if credit is None:
                issues.append(self._issue("FEC_INVALID_CREDIT", raw, "invalid Credit"))
            if debit is not None and credit is not None:
                if debit < 0 or credit < 0:
                    issues.append(
                        self._issue(
                            "FEC_NEGATIVE_AMOUNT",
                            raw,
                            "negative debit/credit amount",
                        )
                    )
                if debit > 0 and credit > 0:
                    issues.append(
                        self._issue(
                            "FEC_DEBIT_AND_CREDIT",
                            raw,
                            "both Debit and Credit are positive",
                        )
                    )
                if debit == 0 and credit == 0:
                    issues.append(self._issue("FEC_ZERO_LINE", raw, "zero debit and credit"))

            currency_code = (fields.get("Idevise") or "").strip().upper()
            currency_amount = (fields.get("Montantdevise") or "").strip()
            if currency_amount and not currency_code:
                issues.append(
                    self._issue(
                        "FEC_UNKNOWN_CURRENCY",
                        raw,
                        "Montantdevise is set without Idevise",
                    )
                )
            if currency_code:
                try:
                    lookup_currency(currency_code)
                except Exception:
                    issues.append(
                        self._issue(
                            "FEC_UNKNOWN_CURRENCY",
                            raw,
                            f"unknown currency {currency_code!r}",
                        )
                    )

        checksum_counts = Counter(record.row_checksum for record in records if record.row_checksum)
        duplicates = {checksum for checksum, count in checksum_counts.items() if count > 1}
        for raw in records:
            if raw.row_checksum in duplicates:
                issues.append(
                    ImportIssue(
                        issue_code="FEC_DUPLICATE_LINE",
                        severity=ImportIssueSeverity.WARNING,
                        blocking=False,
                        message="duplicate row candidate detected from canonical row hash",
                        source_record_refs=(raw.source_ref,),
                        metadata={"strategy": "ROW_HASH", "action": "WARN_ONLY"},
                    )
                )
        return tuple(issues)

    def validate_normalized(
        self,
        records: tuple[NormalizedImportRecord, ...],
    ) -> tuple[ImportIssue, ...]:
        issues: list[ImportIssue] = []
        buckets: dict[str, list[NormalizedImportRecord]] = defaultdict(list)
        for record in records:
            buckets[record.source_entry_key.value].append(record)

        for key, group in sorted(buckets.items()):
            refs = tuple(record.source_record_ref for record in group)
            if len(group) < 2:
                issues.append(
                    ImportIssue(
                        issue_code="FEC_UNBALANCED_ENTRY",
                        severity=ImportIssueSeverity.ERROR,
                        blocking=True,
                        message="FEC entry contains fewer than two lines",
                        source_record_refs=refs,
                        source_entry_key=group[0].source_entry_key,
                    )
                )
                continue
            dates = {record.accounting_date for record in group}
            journals = {record.source_journal_code for record in group}
            debit = sum((record.debit for record in group), Decimal(0))
            credit = sum((record.credit for record in group), Decimal(0))
            if len(dates) != 1 or len(journals) != 1 or debit != credit:
                issues.append(
                    ImportIssue(
                        issue_code="FEC_UNBALANCED_ENTRY",
                        severity=ImportIssueSeverity.ERROR,
                        blocking=True,
                        message=(
                            "FEC entry is inconsistent or unbalanced "
                            f"(key={key}, debit={debit}, credit={credit})"
                        ),
                        source_record_refs=refs,
                        source_entry_key=group[0].source_entry_key,
                        expected=str(debit),
                        actual=str(credit),
                    )
                )

        total_debit = sum((record.debit for record in records), Decimal(0))
        total_credit = sum((record.credit for record in records), Decimal(0))
        if total_debit != total_credit:
            issues.append(
                ImportIssue(
                    issue_code="FEC_GLOBAL_UNBALANCED",
                    severity=ImportIssueSeverity.CRITICAL,
                    blocking=True,
                    message="global FEC debit and credit totals differ",
                    expected=str(total_debit),
                    actual=str(total_credit),
                )
            )
        return tuple(issues)

    def report(
        self,
        *,
        batch_id: str,
        raw_records: tuple[RawImportRecord, ...],
        normalized_records: tuple[NormalizedImportRecord, ...],
    ) -> ImportValidationReport:
        issues = self.validate_raw(raw_records) + self.validate_normalized(normalized_records)
        rejected_refs = {
            ref for issue in issues if issue.blocking for ref in issue.source_record_refs
        }
        warning_refs = {
            ref for issue in issues if not issue.blocking for ref in issue.source_record_refs
        }
        total_debit = sum((record.debit for record in normalized_records), Decimal(0))
        total_credit = sum((record.credit for record in normalized_records), Decimal(0))
        return ImportValidationReport(
            batch_id=batch_id,
            issues=issues,
            total_records=len(raw_records),
            accepted_records=max(0, len(raw_records) - len(rejected_refs)),
            rejected_records=len(rejected_refs),
            warning_records=len(warning_refs),
            unmapped_accounts=0,
            unmapped_journals=0,
            total_debit=total_debit,
            total_credit=total_credit,
        )

    def _date_in_fiscal_year(self, value: date) -> bool:
        start = self.descriptor.fiscal_year_start
        end = self.descriptor.fiscal_year_end
        if start is not None and value < start:
            return False
        if end is not None and value > end:
            return False
        return True

    @staticmethod
    def _raw_date(value: str | None) -> date | None:
        raw = (value or "").strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%Y%m%d").date()
        except ValueError:
            return None

    @staticmethod
    def _raw_decimal(value: str | None) -> Decimal | None:
        raw = (value or "").strip().replace(" ", "").replace(",", ".")
        if not raw:
            return Decimal(0)
        try:
            return Decimal(raw)
        except InvalidOperation:
            return None

    @staticmethod
    def _issue(code: str, raw: RawImportRecord, message: str) -> ImportIssue:
        return ImportIssue(
            issue_code=code,
            severity=ImportIssueSeverity.ERROR,
            blocking=True,
            message=message,
            source_record_refs=(raw.source_ref,),
        )


__all__ = ["FECValidator"]
