"""Composed French FEC adapter over the generic accounting-import contracts."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.imports.batch import ImportMode
from pyaccountingkit.domain.imports.source_artifact import ImportSourceFingerprint, SourceArtifact
from pyaccountingkit.ports.accounting_import import ParsedImport

from .controls import FECValidator
from .grouping import FECGroupingStrategy
from .normalizer import FECNormalizer
from .parser import FECParser
from .schema import FECSourceDescriptor


@dataclass(frozen=True, slots=True)
class FECAdapterCapabilities:
    raw_preservation: bool = True
    source_checksum: bool = True
    source_entry_key: bool = True
    source_line_number: bool = True
    auxiliary_fields: bool = True
    trusted_posted_history: bool = True
    streaming: bool = False


class FECAdapter:
    """Specialized French adapter; no FEC field leaks into the generic domain."""

    adapter_id = "fec-fr"
    adapter_version = "0.3.0a2"
    capabilities = FECAdapterCapabilities()

    def __init__(self, descriptor: FECSourceDescriptor | None = None) -> None:
        self.descriptor = descriptor or FECSourceDescriptor()
        self._parser = FECParser(self.descriptor)
        self._normalizer = FECNormalizer(self.descriptor)
        self._validator = FECValidator(self.descriptor)
        self._grouping = FECGroupingStrategy()

    def parser(self) -> FECParser:
        return self._parser

    def normalizer(self) -> FECNormalizer:
        return self._normalizer

    def validator(self) -> FECValidator:
        return self._validator

    def grouping(self) -> FECGroupingStrategy:
        return self._grouping

    def parse(
        self,
        artifact: SourceArtifact,
        *,
        batch_id: str,
        payload: bytes,
    ) -> ParsedImport:
        return self._parser.parse(artifact, batch_id=batch_id, payload=payload)

    def source_fingerprint(
        self,
        artifact: SourceArtifact,
        *,
        entity_id: EntityId,
        fiscal_year_id: str | None = None,
        source_business_key: str | None = None,
    ) -> ImportSourceFingerprint:
        return ImportSourceFingerprint(
            checksum=artifact.checksum,
            entity_id=str(entity_id),
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            fiscal_year_id=fiscal_year_id,
            source_business_key=source_business_key,
        )

    @staticmethod
    def validate_import_mode(mode: ImportMode, *, trusted_source: bool) -> None:
        if mode is ImportMode.TRUSTED_POSTED_HISTORY_IMPORT and not trusted_source:
            raise ValueError(
                "TRUSTED_POSTED_HISTORY_IMPORT requires an explicitly trusted FEC source"
            )


__all__ = ["FECAdapter", "FECAdapterCapabilities"]
