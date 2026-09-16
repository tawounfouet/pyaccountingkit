"""Replay qualification for LOT-17 regulatory reporting and export evidence."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pyaccountingkit.adapters.in_memory.reference_reporting_model_provider import (
    InMemoryReferenceReportingModelProvider,
)
from pyaccountingkit.adapters.regulatory.json_renderer import CanonicalJSONRegulatoryRenderer
from pyaccountingkit.application.reporting.regulatory_export_service import RegulatoryExportService
from pyaccountingkit.application.reporting.regulatory_reporting_service import (
    RegulatoryReportingService,
)
from pyaccountingkit.core.clock import FrozenClock
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId, IdFactory
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.reference_reporting_model import (
    ReferenceReportingModel,
    ReferenceReportingNode,
    ReferenceReportingNodeType,
)
from pyaccountingkit.domain.reporting.regulatory_export import RegulatoryExportDefinition
from pyaccountingkit.domain.reporting.regulatory_mapping import (
    RegulatoryMappingProvenance,
    RegulatoryMappingSet,
    RegulatoryMappingSetStatus,
    RegulatoryMappingStatus,
    RegulatoryStatementMapping,
)
from pyaccountingkit.domain.reporting.regulatory_profile import (
    RegulatoryProfileStatus,
    RegulatoryReportingProfile,
)
from pyaccountingkit.domain.reporting.report_snapshot import (
    ReportSnapshot,
    ReportSnapshotLine,
    ReportSnapshotStatus,
)
from pyaccountingkit.domain.reporting.statement_definition import FinancialStatementType

ENTITY = EntityId("replay-regulatory-entity")
AS_OF = date(2026, 12, 31)


def _coordinates() -> tuple[
    ReportSnapshot,
    ReferenceReportingModel,
    RegulatoryReportingProfile,
    RegulatoryMappingSet,
    RegulatoryExportDefinition,
]:
    snapshot = ReportSnapshot(
        snapshot_id="report-snapshot-2026",
        accounting_entity_id=ENTITY,
        report_type=FinancialStatementType.BALANCE_SHEET,
        source_period_id="FY2026",
        source_checksum="tb-source-checksum",
        statement_definition_id="bs-definition",
        statement_definition_version="1",
        statement_definition_checksum="bs-definition-checksum",
        mapping_set_id="statement-mapping",
        mapping_set_version="1",
        mapping_set_checksum="statement-mapping-checksum",
        result_checksum="financial-result-checksum",
        as_of=AS_OF,
        created_at=datetime(2026, 12, 31, tzinfo=UTC),
        status=ReportSnapshotStatus.PUBLISHED,
        lines=(
            ReportSnapshotLine(
                code="FS_ASSETS",
                label="Assets",
                amount=Money.from_str("100.00", EUR),
                comparative_amount=Money.from_str("90.00", EUR),
            ),
        ),
        checksum="sealed-report-snapshot",
    )
    model = ReferenceReportingModel(
        model_id="reg-model",
        model_code="BALANCE_SHEET",
        framework="PCG",
        edition="2026",
        reference_snapshot_id="reference-2026",
        reference_snapshot_checksum="c" * 64,
        nodes=(
            ReferenceReportingNode(
                node_id="assets",
                code="REG_ASSETS",
                label="Regulatory assets",
                node_type=ReferenceReportingNodeType.TOTAL,
                order=1,
                required=True,
                account_hints_executable=False,
            ),
        ),
    )
    profile = RegulatoryReportingProfile(
        profile_id="reg-profile",
        code="PCG_REPLAY",
        framework="PCG",
        jurisdiction="FR",
        edition="2026",
        version="1",
        status=RegulatoryProfileStatus.ACTIVE,
        reference_snapshot_id=model.reference_snapshot_id,
        reference_snapshot_checksum=model.reference_snapshot_checksum,
        financial_statement_definition_ids=(snapshot.statement_definition_id,),
        regulatory_mapping_set_id="reg-map",
        export_definition_ids=("reg-json",),
        effective_from=date(2026, 1, 1),
        accounting_entity_id=ENTITY,
    )
    mapping_set = RegulatoryMappingSet(
        mapping_set_id="reg-map",
        accounting_entity_id=ENTITY,
        profile_id=profile.profile_id,
        reference_model_id=model.model_id,
        version="1",
        status=RegulatoryMappingSetStatus.ACTIVE,
        mappings=(
            RegulatoryStatementMapping(
                mapping_id="map-assets",
                statement_line_code="FS_ASSETS",
                reference_node_id="assets",
                allocation=Decimal("1"),
                status=RegulatoryMappingStatus.VALIDATED,
                provenance=RegulatoryMappingProvenance.MANUAL,
                effective_from=date(2026, 1, 1),
            ),
        ),
        effective_from=date(2026, 1, 1),
    )
    export_definition = RegulatoryExportDefinition(
        export_definition_id="reg-json",
        code="REG_JSON",
        version="1",
        profile_id=profile.profile_id,
        renderer_id="canonical-json-v1",
        media_type="application/json",
        schema_version="1",
        effective_from=date(2026, 1, 1),
        required_node_ids=("assets",),
    )
    return snapshot, model, profile, mapping_set, export_definition


def _run(
    *,
    export_time: datetime,
    id_seed: int,
) -> tuple[str, str, str, str]:
    snapshot, model, profile, mapping_set, export_definition = _coordinates()
    reporting = RegulatoryReportingService(InMemoryReferenceReportingModelProvider((model,))).build(
        snapshot=snapshot,
        profile=profile,
        mapping_set=mapping_set,
        model_code=model.model_code,
    )
    counter = iter((id_seed, id_seed + 1))
    exported = RegulatoryExportService(
        renderer=CanonicalJSONRegulatoryRenderer(),
        clock=FrozenClock(export_time),
        id_factory=IdFactory(lambda _: next(counter)),
    ).export(
        report=reporting.report,
        validation=reporting.validation,
        profile=profile,
        definition=export_definition,
    )
    return (
        reporting.report.checksum,
        reporting.validation.checksum,
        exported.artifact.payload_checksum,
        exported.evidence.checksum,
    )


def test_regulatory_report_export_and_evidence_replay_are_deterministic() -> None:
    first = _run(export_time=datetime(2027, 1, 1, tzinfo=UTC), id_seed=1)
    replay = _run(export_time=datetime(2028, 6, 1, tzinfo=UTC), id_seed=100)

    assert first == replay
