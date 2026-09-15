"""Normalize FEC-specific rows into the generic accounting import vocabulary."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Mapping

from pyaccountingkit.core.currency import Currency, lookup_currency
from pyaccountingkit.domain.imports.normalized_record import NormalizedImportRecord, SourceEntryKey
from pyaccountingkit.ports.accounting_import import ParsedImport

from .schema import FECSourceDescriptor


class FECNormalizationError(ValueError):
    """A syntactically parsed FEC row cannot be normalized safely."""


class FECNormalizer:
    normalizer_version = "fec-normalizer/1"

    def __init__(self, descriptor: FECSourceDescriptor | None = None) -> None:
        self.descriptor = descriptor or FECSourceDescriptor()

    def normalize(
        self,
        parsed: ParsedImport,
        *,
        batch_id: str,
    ) -> tuple[NormalizedImportRecord, ...]:
        normalized: list[NormalizedImportRecord] = []
        for raw in parsed.records:
            fields = raw.raw_fields
            journal_code = self._required(fields, "JournalCode", raw.source_ref)
            entry_number = self._required(fields, "EcritureNum", raw.source_ref)
            account_number = self._required(fields, "CompteNum", raw.source_ref)
            entry_date = self._parse_date(
                self._required(fields, "EcritureDate", raw.source_ref),
                field="EcritureDate",
                source_ref=raw.source_ref,
            )
            debit = self._parse_decimal(
                fields.get("Debit"), field="Debit", source_ref=raw.source_ref
            )
            credit = self._parse_decimal(
                fields.get("Credit"), field="Credit", source_ref=raw.source_ref
            )
            currency = self._currency(fields)

            metadata = {
                "fec.JournalLib": fields.get("JournalLib") or "",
                "fec.CompteLib": fields.get("CompteLib") or "",
                "fec.CompAuxLib": fields.get("CompAuxLib") or "",
                "fec.PieceRef": fields.get("PieceRef") or "",
                "fec.EcritureLet": fields.get("EcritureLet") or "",
                "fec.DateLet": fields.get("DateLet") or "",
                "fec.ValidDate": fields.get("ValidDate") or "",
                "fec.Montantdevise": fields.get("Montantdevise") or "",
                "fec.Idevise": fields.get("Idevise") or "",
                "fec.row_checksum": raw.row_checksum or "",
                "fec.source_line_number": str(raw.source_line_number or ""),
            }
            normalized.append(
                NormalizedImportRecord(
                    batch_id=batch_id,
                    normalized_record_id=f"fec:{raw.record_index}",
                    source_record_ref=raw.source_ref,
                    source_entry_key=SourceEntryKey(f"{journal_code}:{entry_number}"),
                    source_line_key=str(raw.source_line_number or raw.record_index),
                    source_journal_code=journal_code,
                    source_account_code=account_number,
                    accounting_date=entry_date,
                    document_date=self._optional_date(fields.get("PieceDate"), raw.source_ref),
                    description=(fields.get("EcritureLib") or None),
                    debit=debit,
                    credit=credit,
                    currency=currency,
                    auxiliary_code=(fields.get("CompAuxNum") or None),
                    metadata=metadata,
                )
            )
        return tuple(normalized)

    def _currency(self, fields: Mapping[str, str | None]) -> Currency:
        code = (fields.get("Idevise") or self.descriptor.default_currency).strip().upper()
        try:
            return lookup_currency(code)
        except Exception as exc:
            raise FECNormalizationError(f"unknown FEC currency {code!r}") from exc

    @staticmethod
    def _required(fields: Mapping[str, str | None], name: str, source_ref: str) -> str:
        value = fields.get(name)
        if value is None or not value.strip():
            raise FECNormalizationError(f"{source_ref}: missing required FEC field {name}")
        return value.strip()

    @staticmethod
    def _parse_decimal(value: str | None, *, field: str, source_ref: str) -> Decimal:
        raw = (value or "").strip().replace(" ", "").replace(",", ".")
        if raw == "":
            return Decimal(0)
        try:
            return Decimal(raw)
        except InvalidOperation as exc:
            raise FECNormalizationError(
                f"{source_ref}: invalid decimal in {field}: {value!r}"
            ) from exc

    @staticmethod
    def _parse_date(value: str, *, field: str, source_ref: str) -> date:
        try:
            return datetime.strptime(value, "%Y%m%d").date()
        except ValueError as exc:
            raise FECNormalizationError(
                f"{source_ref}: invalid YYYYMMDD date in {field}: {value!r}"
            ) from exc

    @classmethod
    def _optional_date(cls, value: str | None, source_ref: str) -> date | None:
        if value is None or not value.strip():
            return None
        return cls._parse_date(value.strip(), field="PieceDate", source_ref=source_ref)


__all__ = ["FECNormalizationError", "FECNormalizer"]
