"""Ports owned by the source-format-neutral accounting import core."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from pyaccountingkit.core.identifiers import EntityId, PeriodId
from pyaccountingkit.domain.imports.normalized_record import NormalizedImportRecord
from pyaccountingkit.domain.imports.raw_record import RawImportRecord
from pyaccountingkit.domain.imports.source_artifact import SourceArtifact


@dataclass(frozen=True, slots=True)
class ParsedImport:
    records: tuple[RawImportRecord, ...]
    parser_version: str
    warnings: tuple[str, ...] = ()


class AccountingImportParser(Protocol):
    def parse(
        self,
        artifact: SourceArtifact,
        *,
        batch_id: str,
        payload: bytes,
    ) -> ParsedImport: ...


class AccountingImportNormalizer(Protocol):
    def normalize(
        self,
        parsed: ParsedImport,
        *,
        batch_id: str,
    ) -> tuple[NormalizedImportRecord, ...]: ...


class ImportPeriodResolver(Protocol):
    def resolve(self, entity_id: EntityId, accounting_date: date) -> PeriodId: ...


__all__ = [
    "AccountingImportNormalizer",
    "AccountingImportParser",
    "ImportPeriodResolver",
    "ParsedImport",
]
