"""Application service exporting validated regulatory reports without recalculation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pyaccountingkit.core.clock import ClockProtocol
from pyaccountingkit.core.identifiers import IdFactory
from pyaccountingkit.domain.reporting.errors import (
    RegulatoryEvidenceMismatchError,
    RegulatoryExportIncompatibleError,
    RegulatoryValidationError,
)
from pyaccountingkit.domain.reporting.regulatory_export import (
    RegulatoryExportArtifact,
    RegulatoryExportDefinition,
)
from pyaccountingkit.domain.reporting.regulatory_profile import RegulatoryReportingProfile
from pyaccountingkit.domain.reporting.regulatory_report import RegulatoryReport
from pyaccountingkit.domain.reporting.regulatory_validation import RegulatoryValidationReport
from pyaccountingkit.domain.reporting.report_evidence import ReportEvidenceBundle
from pyaccountingkit.ports.regulatory_reporting import RegulatoryRendererProtocol


@dataclass(frozen=True, slots=True)
class RegulatoryExportResult:
    artifact: RegulatoryExportArtifact
    evidence: ReportEvidenceBundle


class RegulatoryExportService:
    """Render an already-computed regulatory report and seal its evidence chain."""

    def __init__(
        self,
        *,
        renderer: RegulatoryRendererProtocol,
        clock: ClockProtocol,
        id_factory: IdFactory,
    ) -> None:
        self._renderer = renderer
        self._clock = clock
        self._id_factory = id_factory

    def export(
        self,
        *,
        report: RegulatoryReport,
        validation: RegulatoryValidationReport,
        profile: RegulatoryReportingProfile,
        definition: RegulatoryExportDefinition,
    ) -> RegulatoryExportResult:
        if validation.has_blocking_failures:
            raise RegulatoryValidationError(
                "regulatory report has blocking validation failures and cannot be exported"
            )
        if (
            report.profile_id != profile.profile_id
            or report.profile_version != profile.version
            or report.profile_checksum != profile.checksum
        ):
            raise RegulatoryEvidenceMismatchError(
                "regulatory report profile coordinates do not match export profile"
            )
        if definition.profile_id != profile.profile_id:
            raise RegulatoryExportIncompatibleError(
                "regulatory export definition targets a different profile"
            )
        if definition.export_definition_id not in profile.export_definition_ids:
            raise RegulatoryExportIncompatibleError(
                "regulatory export definition is not pinned by the profile"
            )
        if definition.renderer_id != self._renderer.renderer_id:
            raise RegulatoryExportIncompatibleError(
                "regulatory export definition requires a different renderer"
            )
        if not definition.effective_on(report.as_of):
            raise RegulatoryExportIncompatibleError(
                "regulatory export definition is not effective on report date"
            )

        present_node_ids = {node.node_id for node in report.nodes}
        missing = sorted(set(definition.required_node_ids) - present_node_ids)
        if missing:
            raise RegulatoryExportIncompatibleError(
                f"regulatory export is missing required nodes: {missing!r}"
            )

        payload = self._renderer.render(report, definition)
        payload_checksum = hashlib.sha256(payload).hexdigest()
        artifact = RegulatoryExportArtifact(
            artifact_id=self._id_factory.new("reg_export"),
            accounting_entity_id=report.accounting_entity_id,
            regulatory_report_checksum=report.checksum,
            profile_id=report.profile_id,
            profile_version=report.profile_version,
            reference_snapshot_id=report.reference_snapshot_id,
            export_definition_id=definition.export_definition_id,
            export_definition_version=definition.version,
            media_type=definition.media_type,
            payload_checksum=payload_checksum,
            generated_at=self._clock.now(),
            payload=payload,
        )
        evidence = ReportEvidenceBundle.build(
            evidence_id=self._id_factory.new("report_evidence"),
            accounting_entity_id=report.accounting_entity_id,
            report_snapshot_id=report.source_report_snapshot_id,
            report_snapshot_checksum=report.source_report_checksum,
            regulatory_report_checksum=report.checksum,
            profile_checksum=report.profile_checksum,
            reference_snapshot_id=report.reference_snapshot_id,
            reference_snapshot_checksum=report.reference_snapshot_checksum,
            reference_model_checksum=report.reference_model_checksum,
            regulatory_mapping_checksum=report.regulatory_mapping_set_checksum,
            validation_checksum=validation.checksum,
            export_definition_checksum=definition.checksum,
            export_artifact_payload_checksum=artifact.payload_checksum,
            source_refs=(f"report_snapshot:{report.source_report_snapshot_id}",),
        )
        return RegulatoryExportResult(artifact=artifact, evidence=evidence)


__all__ = ["RegulatoryExportResult", "RegulatoryExportService"]
