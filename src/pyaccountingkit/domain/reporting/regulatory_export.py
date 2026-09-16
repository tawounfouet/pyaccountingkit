"""Regulatory export definitions and immutable payload artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.reporting.errors import RegulatoryExportError


@dataclass(frozen=True, slots=True)
class RegulatoryExportDefinition:
    """Versioned renderer contract; it contains no accounting calculation rules."""

    export_definition_id: str
    code: str
    version: str
    profile_id: str
    renderer_id: str
    media_type: str
    schema_version: str
    effective_from: date
    required_node_ids: tuple[str, ...] = ()
    effective_to: date | None = None

    def __post_init__(self) -> None:
        required = {
            "export_definition_id": self.export_definition_id,
            "code": self.code,
            "version": self.version,
            "profile_id": self.profile_id,
            "renderer_id": self.renderer_id,
            "media_type": self.media_type,
            "schema_version": self.schema_version,
        }
        for name, value in required.items():
            if not value.strip():
                raise RegulatoryExportError(f"{name} must not be empty")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise RegulatoryExportError("export effective_to cannot precede effective_from")
        if len(self.required_node_ids) != len(set(self.required_node_ids)):
            raise RegulatoryExportError("required regulatory export node ids must be unique")
        if any(not node_id.strip() for node_id in self.required_node_ids):
            raise RegulatoryExportError("required regulatory export node ids must not be empty")

    def effective_on(self, value: date) -> bool:
        if value < self.effective_from:
            return False
        return self.effective_to is None or value <= self.effective_to

    @property
    def checksum(self) -> str:
        payload = {
            "export_definition_id": self.export_definition_id,
            "code": self.code,
            "version": self.version,
            "profile_id": self.profile_id,
            "renderer_id": self.renderer_id,
            "media_type": self.media_type,
            "schema_version": self.schema_version,
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "required_node_ids": sorted(self.required_node_ids),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class RegulatoryExportArtifact:
    """Sealed bytes rendered from an already-computed regulatory report."""

    artifact_id: str
    accounting_entity_id: EntityId
    regulatory_report_checksum: str
    profile_id: str
    profile_version: str
    reference_snapshot_id: str
    export_definition_id: str
    export_definition_version: str
    media_type: str
    payload_checksum: str
    generated_at: datetime
    payload: bytes

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise RegulatoryExportError("regulatory export artifact id must not be empty")
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise RegulatoryExportError("regulatory export generated_at must be timezone-aware")
        actual = hashlib.sha256(self.payload).hexdigest()
        if self.payload_checksum != actual:
            raise RegulatoryExportError("regulatory export payload checksum mismatch")


__all__ = ["RegulatoryExportArtifact", "RegulatoryExportDefinition"]
