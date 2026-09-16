"""Immutable evidence bundles for regulatory report exports and replay."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from pyaccountingkit.core.identifiers import EntityId


@dataclass(frozen=True, slots=True)
class ReportEvidenceBundle:
    """Checksum chain connecting source report, regulation, validation and export."""

    evidence_id: str
    accounting_entity_id: EntityId
    report_snapshot_id: str
    report_snapshot_checksum: str
    regulatory_report_checksum: str
    profile_checksum: str
    reference_snapshot_id: str
    reference_snapshot_checksum: str
    reference_model_checksum: str
    regulatory_mapping_checksum: str
    validation_checksum: str
    export_definition_checksum: str
    export_artifact_payload_checksum: str
    source_refs: tuple[str, ...]
    checksum: str

    @classmethod
    def build(
        cls,
        *,
        evidence_id: str,
        accounting_entity_id: EntityId,
        report_snapshot_id: str,
        report_snapshot_checksum: str,
        regulatory_report_checksum: str,
        profile_checksum: str,
        reference_snapshot_id: str,
        reference_snapshot_checksum: str,
        reference_model_checksum: str,
        regulatory_mapping_checksum: str,
        validation_checksum: str,
        export_definition_checksum: str,
        export_artifact_payload_checksum: str,
        source_refs: tuple[str, ...],
    ) -> ReportEvidenceBundle:
        if not evidence_id.strip():
            raise ValueError("report evidence id must not be empty")
        payload = {
            "accounting_entity_id": str(accounting_entity_id),
            "report_snapshot_id": report_snapshot_id,
            "report_snapshot_checksum": report_snapshot_checksum,
            "regulatory_report_checksum": regulatory_report_checksum,
            "profile_checksum": profile_checksum,
            "reference_snapshot_id": reference_snapshot_id,
            "reference_snapshot_checksum": reference_snapshot_checksum,
            "reference_model_checksum": reference_model_checksum,
            "regulatory_mapping_checksum": regulatory_mapping_checksum,
            "validation_checksum": validation_checksum,
            "export_definition_checksum": export_definition_checksum,
            "export_artifact_payload_checksum": export_artifact_payload_checksum,
            "source_refs": sorted(source_refs),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        checksum = hashlib.sha256(encoded).hexdigest()
        return cls(
            evidence_id=evidence_id,
            accounting_entity_id=accounting_entity_id,
            report_snapshot_id=report_snapshot_id,
            report_snapshot_checksum=report_snapshot_checksum,
            regulatory_report_checksum=regulatory_report_checksum,
            profile_checksum=profile_checksum,
            reference_snapshot_id=reference_snapshot_id,
            reference_snapshot_checksum=reference_snapshot_checksum,
            reference_model_checksum=reference_model_checksum,
            regulatory_mapping_checksum=regulatory_mapping_checksum,
            validation_checksum=validation_checksum,
            export_definition_checksum=export_definition_checksum,
            export_artifact_payload_checksum=export_artifact_payload_checksum,
            source_refs=tuple(sorted(source_refs)),
            checksum=checksum,
        )


__all__ = ["ReportEvidenceBundle"]
