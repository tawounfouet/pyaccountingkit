"""Golden LOT-17 scenario for a PCG regulatory reporting projection."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pyaccountingkit.adapters.in_memory.reference_reporting_model_provider import (
    InMemoryReferenceReportingModelProvider,
)
from pyaccountingkit.application.reporting.regulatory_reporting_service import (
    RegulatoryReportingService,
)
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.reference_reporting_model import (
    ReferenceReportingModel,
    ReferenceReportingNode,
    ReferenceReportingNodeType,
)
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

ENTITY = EntityId("golden-pcg-entity")
AS_OF = date(2026, 12, 31)


def test_pcg_regulatory_reporting_golden_projection() -> None:
    snapshot = ReportSnapshot(
        snapshot_id="pcg-financial-snapshot-2026",
        accounting_entity_id=ENTITY,
        report_type=FinancialStatementType.BALANCE_SHEET,
        source_period_id="FY2026",
        source_checksum="pcg-tb-2026",
        statement_definition_id="pcg-bs-definition",
        statement_definition_version="2026.1",
        statement_definition_checksum="pcg-bs-definition-checksum",
        mapping_set_id="pcg-statement-map",
        mapping_set_version="2026.1",
        mapping_set_checksum="pcg-statement-map-checksum",
        result_checksum="pcg-financial-result-checksum",
        as_of=AS_OF,
        created_at=datetime(2026, 12, 31, tzinfo=UTC),
        status=ReportSnapshotStatus.PUBLISHED,
        lines=(
            ReportSnapshotLine(
                code="FS_ASSETS",
                label="Total actif",
                amount=Money.from_str("125000.00", EUR),
            ),
            ReportSnapshotLine(
                code="FS_LIABILITIES_EQUITY",
                label="Total passif et capitaux propres",
                amount=Money.from_str("125000.00", EUR),
            ),
        ),
        checksum="pcg-financial-snapshot-checksum",
    )
    model = ReferenceReportingModel(
        model_id="pcg-reg-bs-model",
        model_code="BALANCE_SHEET",
        framework="PCG",
        edition="2026",
        reference_snapshot_id="pcg-reference-2026",
        reference_snapshot_checksum="a" * 64,
        nodes=(
            ReferenceReportingNode(
                node_id="reg-assets",
                code="PCG_ASSETS",
                label="Total actif réglementaire",
                node_type=ReferenceReportingNodeType.TOTAL,
                order=1,
                required=True,
                human_validation_required=True,
                account_hints_executable=False,
                account_hints=("1*", "2*", "3*", "4*", "5*"),
                provenance="pcg-reference-dataset",
            ),
            ReferenceReportingNode(
                node_id="reg-liabilities-equity",
                code="PCG_LIABILITIES_EQUITY",
                label="Total passif réglementaire",
                node_type=ReferenceReportingNodeType.TOTAL,
                order=2,
                required=True,
                account_hints_executable=False,
                provenance="pcg-reference-dataset",
            ),
        ),
    )
    profile = RegulatoryReportingProfile(
        profile_id="pcg-fr-2026-profile",
        code="PCG_FR_2026",
        framework="PCG",
        jurisdiction="FR",
        edition="2026",
        version="1",
        status=RegulatoryProfileStatus.ACTIVE,
        reference_snapshot_id=model.reference_snapshot_id,
        reference_snapshot_checksum=model.reference_snapshot_checksum,
        financial_statement_definition_ids=(snapshot.statement_definition_id,),
        regulatory_mapping_set_id="pcg-reg-map",
        export_definition_ids=("pcg-json",),
        effective_from=date(2026, 1, 1),
        accounting_entity_id=ENTITY,
    )
    mappings = RegulatoryMappingSet(
        mapping_set_id="pcg-reg-map",
        accounting_entity_id=ENTITY,
        profile_id=profile.profile_id,
        reference_model_id=model.model_id,
        version="1",
        status=RegulatoryMappingSetStatus.ACTIVE,
        mappings=(
            RegulatoryStatementMapping(
                mapping_id="pcg-assets",
                statement_line_code="FS_ASSETS",
                reference_node_id="reg-assets",
                allocation=Decimal("1"),
                status=RegulatoryMappingStatus.VALIDATED,
                provenance=RegulatoryMappingProvenance.MANUAL,
                effective_from=date(2026, 1, 1),
            ),
            RegulatoryStatementMapping(
                mapping_id="pcg-le",
                statement_line_code="FS_LIABILITIES_EQUITY",
                reference_node_id="reg-liabilities-equity",
                allocation=Decimal("1"),
                status=RegulatoryMappingStatus.VALIDATED,
                provenance=RegulatoryMappingProvenance.MANUAL,
                effective_from=date(2026, 1, 1),
            ),
        ),
        effective_from=date(2026, 1, 1),
    )

    result = RegulatoryReportingService(InMemoryReferenceReportingModelProvider((model,))).build(
        snapshot=snapshot,
        profile=profile,
        mapping_set=mappings,
        model_code="BALANCE_SHEET",
    )

    assert result.report.node("PCG_ASSETS").amount == Money.from_str("125000.00", EUR)
    assert result.report.node("PCG_LIABILITIES_EQUITY").amount == Money.from_str("125000.00", EUR)
    assert result.report.node("PCG_ASSETS").mapping_provenances == ("MANUAL",)
    assert result.report.node("PCG_ASSETS").account_hints_executable is False
    assert result.report.node("PCG_ASSETS").human_validation_required is True
    assert result.validation.is_valid is True
