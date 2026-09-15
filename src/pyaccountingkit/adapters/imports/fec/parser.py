"""Strict, lossless parser for French FEC text files."""

from __future__ import annotations

import csv
import hashlib
import io

from pyaccountingkit.domain.imports.raw_record import RawImportRecord
from pyaccountingkit.domain.imports.source_artifact import SourceArtifact
from pyaccountingkit.ports.accounting_import import ParsedImport

from .schema import FEC_FIELD_NAMES, FECSourceDescriptor, validate_fec_header


class FECParseError(ValueError):
    """The FEC source cannot be parsed without losing structural integrity."""


class FECParser:
    parser_version = "fec-parser/1"

    def __init__(self, descriptor: FECSourceDescriptor | None = None) -> None:
        self.descriptor = descriptor or FECSourceDescriptor()

    def parse(
        self,
        artifact: SourceArtifact,
        *,
        batch_id: str,
        payload: bytes,
    ) -> ParsedImport:
        checksum = hashlib.sha256(payload).hexdigest()
        if checksum != artifact.checksum:
            raise FECParseError("FEC payload checksum does not match SourceArtifact")
        try:
            text = payload.decode(self.descriptor.encoding)
        except UnicodeDecodeError as exc:
            raise FECParseError(
                f"cannot decode FEC payload with {self.descriptor.encoding!r}"
            ) from exc

        delimiter = self.descriptor.delimiter or self._detect_delimiter(text)
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        try:
            header = tuple(next(reader))
        except StopIteration as exc:
            raise FECParseError("empty FEC file") from exc
        try:
            validate_fec_header(header)
        except ValueError as exc:
            raise FECParseError(str(exc)) from exc

        records: list[RawImportRecord] = []
        for record_index, row in enumerate(reader):
            source_line_number = record_index + 2
            if not row or all(value == "" for value in row):
                continue
            if len(row) != len(FEC_FIELD_NAMES):
                raise FECParseError(
                    f"line {source_line_number}: expected {len(FEC_FIELD_NAMES)} fields, "
                    f"got {len(row)}"
                )
            raw_fields = dict(zip(FEC_FIELD_NAMES, row, strict=True))
            records.append(
                RawImportRecord(
                    batch_id=batch_id,
                    record_index=record_index,
                    source_line_number=source_line_number,
                    source_record_id=f"line:{source_line_number}",
                    raw_fields=raw_fields,
                    provenance={
                        "source_type": "FEC",
                        "artifact_ref": artifact.artifact_ref,
                        "parser_version": self.parser_version,
                    },
                )
            )
        return ParsedImport(records=tuple(records), parser_version=self.parser_version)

    @staticmethod
    def _detect_delimiter(text: str) -> str:
        lines = text.splitlines()
        first_line = lines[0] if lines else ""
        candidates = ("\t", "|", ";")
        counts = {delimiter: first_line.count(delimiter) for delimiter in candidates}
        delimiter, count = max(counts.items(), key=lambda item: item[1])
        if count != len(FEC_FIELD_NAMES) - 1:
            raise FECParseError("unable to detect a canonical FEC delimiter")
        return delimiter


__all__ = ["FECParseError", "FECParser"]
