"""LOT-17 qualification for regulatory rendering, export and evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime

import pytest

from pyaccountingkit.adapters.regulatory.json_renderer import CanonicalJSONRegulatoryRenderer
from pyaccountingkit.application.reporting.regulatory_export_service import RegulatoryExportService
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId, IdFactory
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.errors import RegulatoryValidationError
from pyaccountingkit.domain.reporting.reference_reporting_model import ReferenceReportingValueType
from pyaccountingkit.domain.reporting.regulatory_export import RegulatoryExportDefinition
from pyaccountingkit.domain.reporting.regulatory_profile import (
    RegulatoryProfileStatus,
    RegulatoryReportingProfile,
)
from pyaccountingkit.domain.reporting.regulatory_report import (
    RegulatoryNodeValue,
    RegulatoryReport,
)
from pyaccountingkit.domain.reporting.regulatory_validation import (
    RegulatoryValidationReport,
    RegulatoryValidationResult,
    RegulatoryValidationSeverity,
    RegulatoryValidationStatus,
)

ENTITY = EntityId("entity-a")
AS_OF = date(2026, 12, 31)


def _profile() -> RegulatoryReportingProfile:
    return RegulatoryReportingProfile(
        profile_id="pcg-profile",
        code="PCG_FR_2026",
        framework="PCG",
        jurisdiction="FR",
        edition="2026",
        version="1",
        status=RegulatoryProfileStatus.ACTIVE,
        reference_snapshot_id="ref-pcg-2026",
        reference_snapshot_checksum="a" * 64,
        financial_statement_definition_ids=("bs-pcg",),
        regulatory_mapping_set_id="reg-map-1",
        export_definition_ids=("json-pcg",),
        effective_from=date(2026, 1, 1),
        accounting_entity_id=ENTITY,
    )


def _report(profile: RegulatoryReportingProfile) -> RegulatoryReport:
    return RegulatoryReport.build(
        accounting_entity_id=ENTITY,
        profile_id=profile.profile_id,
        profile_version=profile.version,
        profile_checksum=profile.checksum,
        framework=profile.framework,
        jurisdiction=profile.jurisdiction,
        edition=profile.edition,
        reference_snapshot_id=profile.reference_snapshot_id,
        reference_snapshot_checksum=profile.reference_snapshot_checksum,
        reference_model_id="pcg-bs-model",
        reference_model_checksum="model-checksum",
        source_report_snapshot_id="financial-snapshot-1",
        source_report_checksum="financial-snapshot-checksum",
        regulatory_mapping_set_id="reg-map-1",
        regulatory_mapping_set_version="1",
        regulatory_mapping_set_checksum="reg-map-checksum",
        as_of=AS_OF,
        nodes=(
            RegulatoryNodeValue(
                node_id="assets",
                code="REG_ASSETS",
                label="Assets",
                value_type=ReferenceReportingValueType.MONEY,
                amount=Money.from_str("100", EUR),
                comparative_amount=Money.from_str("80", EUR),
                source_statement_lines=("FS_ASSETS",),
                mapping_ids=("m1",),
                mapping_provenances=("MANUAL",),
                human_validation_required=False,
                account_hints_executable=False,
            ),
        ),
    )


def _definition() -> RegulatoryExportDefinition:
    return RegulatoryExportDefinition(
        export_definition_id="json-pcg",
        code="PCG_JSON",
        version="1",
        profile_id="pcg-profile",
        renderer_id="canonical-json-v1",
        media_type="application/json",
        schema_version="1",
        effective_from=date(2026, 1, 1),
        required_node_ids=("assets",),
    )


def _valid_validation() -> RegulatoryValidationReport:
    return RegulatoryValidationReport.build(
        (
            RegulatoryValidationResult(
                rule_id="REQUIRED_MAPPING:REG_ASSETS",
                severity=RegulatoryValidationSeverity.BLOCKING,
                status=RegulatoryValidationStatus.PASS,
                message="mapped",
                node_id="assets",
            ),
        )
    )


def _service() -> RegulatoryExportService:
    values = iter((1, 2))
    return RegulatoryExportService(
        renderer=CanonicalJSONRegulatoryRenderer(),
        clock=FrozenClock(datetime(2027, 1, 2, tzinfo=UTC)),
        id_factory=IdFactory(lambda _: next(values)),
    )


def test_exporter_serializes_precomputed_report_and_seals_evidence() -> None:
    profile = _profile()
    report = _report(profile)
    result = _service().export(
        report=report,
        validation=_valid_validation(),
        profile=profile,
        definition=_definition(),
    )

    decoded = json.loads(result.artifact.payload)
    assert decoded["report_checksum"] == report.checksum
    assert decoded["nodes"][0]["amount"] == "100.00"
    assert result.artifact.payload_checksum == hashlib.sha256(result.artifact.payload).hexdigest()
    assert result.evidence.regulatory_report_checksum == report.checksum
    assert result.evidence.export_artifact_payload_checksum == result.artifact.payload_checksum
    assert result.evidence.validation_checksum == _valid_validation().checksum


def test_canonical_renderer_is_deterministic() -> None:
    profile = _profile()
    report = _report(profile)
    renderer = CanonicalJSONRegulatoryRenderer()

    assert renderer.render(report, _definition()) == renderer.render(report, _definition())


def test_blocking_validation_prevents_export() -> None:
    profile = _profile()
    report = _report(profile)
    failed = RegulatoryValidationReport.build(
        (
            RegulatoryValidationResult(
                rule_id="REQUIRED_MAPPING:REG_ASSETS",
                severity=RegulatoryValidationSeverity.BLOCKING,
                status=RegulatoryValidationStatus.FAIL,
                message="missing mapping",
                node_id="assets",
            ),
        )
    )

    with pytest.raises(RegulatoryValidationError):
        _service().export(
            report=report,
            validation=failed,
            profile=profile,
            definition=_definition(),
        )
