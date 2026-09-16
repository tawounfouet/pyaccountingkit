"""Golden LOT-17 scenario for a SYSCOHADA regulatory reporting projection."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from pyaccountingkit.adapters.in_memory.reference_reporting_model_provider import (
    InMemoryReferenceReportingModelProvider,
)
from pyaccountingkit.application.reporting.regulatory_reporting_service import (
    RegulatoryReportingService,
)
from pyaccountingkit.core.currency import XOF
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

ENTITY = EntityId("golden-syscohada-entity")
AS_OF = date(2026, 12, 31)


def test_syscohada_regulatory_reporting_golden_projection() -> None:
    snapshot = ReportSnapshot(
        snapshot_id="syscohada-financial-snapshot-2026",
        accounting_entity_id=ENTITY,
        report_type=FinancialStatementType.BALANCE_SHEET,
        source_period_id="FY2026",
        source_checksum="syscohada-tb-2026",
        statement_definition_id="syscohada-bs-definition",
        statement_definition_version="2017.1",
        statement_definition_checksum="syscohada-bs-definition-checksum",
        mapping_set_id="syscohada-statement-map",
        mapping_set_version="2017.1",
        mapping_set_checksum="syscohada-statement-map-checksum",
        result_checksum="syscohada-financial-result-checksum",
        as_of=AS_OF,
        created_at=datetime(2026, 12, 31, tzinfo=UTC),
        status=ReportSnapshotStatus.PUBLISHED,
        lines=(
            ReportSnapshotLine(
                code="FS_ASSETS",
                label="Total actif",
                amount=Money.from_str("25000000", XOF),
            ),
            ReportSnapshotLine(
                code="FS_LIABILITIES_EQUITY",
                label="Total passif",
                amount=Money.from_str("25000000", XOF),
            ),
        ),
        checksum="syscohada-financial-snapshot-checksum",
    )
    model = ReferenceReportingModel(
        model_id="syscohada-reg-bs-model",
        model_code="BALANCE_SHEET",
        framework="SYSCOHADA",
        edition="2017",
        reference_snapshot_id="syscohada-reference-2017",
        reference_snapshot_checksum="b" * 64,
        nodes=(
            ReferenceReportingNode(
                node_id="reg-assets",
                code="SYSCOHADA_ASSETS",
                label="Total actif SYSCOHADA",
                node_type=ReferenceReportingNodeType.TOTAL,
                order=1,
                required=True,
                human_validation_required=True,
                account_hints_executable=False,
                account_hints=("2*", "3*", "4*", "5*"),
                provenance="syscohada-reference-dataset",
            ),
            ReferenceReportingNode(
                node_id="reg-liabilities-equity",
                code="SYSCOHADA_LIABILITIES_EQUITY",
                label="Total passif SYSCOHADA",
                node_type=ReferenceReportingNodeType.TOTAL,
                order=2,
                required=True,
                account_hints_executable=False,
                provenance="syscohada-reference-dataset",
            ),
        ),
    )
    profile = RegulatoryReportingProfile(
        profile_id="syscohada-2017-profile",
        code="SYSCOHADA_2017",
        framework="SYSCOHADA",
        jurisdiction="OHADA",
        edition="2017",
        version="1",
        status=RegulatoryProfileStatus.ACTIVE,
        reference_snapshot_id=model.reference_snapshot_id,
        reference_snapshot_checksum=model.reference_snapshot_checksum,
        financial_statement_definition_ids=(snapshot.statement_definition_id,),
        regulatory_mapping_set_id="syscohada-reg-map",
        export_definition_ids=("syscohada-json",),
        effective_from=date(2018, 1, 1),
        accounting_entity_id=ENTITY,
    )
    mappings = RegulatoryMappingSet(
        mapping_set_id="syscohada-reg-map",
        accounting_entity_id=ENTITY,
        profile_id=profile.profile_id,
        reference_model_id=model.model_id,
        version="1",
        status=RegulatoryMappingSetStatus.ACTIVE,
        mappings=(
            RegulatoryStatementMapping(
                mapping_id="syscohada-assets",
                statement_line_code="FS_ASSETS",
                reference_node_id="reg-assets",
                allocation=Decimal("1"),
                status=RegulatoryMappingStatus.VALIDATED,
                provenance=RegulatoryMappingProvenance.VALIDATED_CANDIDATE,
                effective_from=date(2018, 1, 1),
            ),
            RegulatoryStatementMapping(
                mapping_id="syscohada-le",
                statement_line_code="FS_LIABILITIES_EQUITY",
                reference_node_id="reg-liabilities-equity",
                allocation=Decimal("1"),
                status=RegulatoryMappingStatus.VALIDATED,
                provenance=RegulatoryMappingProvenance.MANUAL,
                effective_from=date(2018, 1, 1),
            ),
        ),
        effective_from=date(2018, 1, 1),
    )

    result = RegulatoryReportingService(
        InMemoryReferenceReportingModelProvider((model,))
    ).build(
        snapshot=snapshot,
        profile=profile,
        mapping_set=mappings,
        model_code="BALANCE_SHEET",
    )

    assert result.report.node("SYSCOHADA_ASSETS").amount == Money.from_str("25000000", XOF)
    assert result.report.node("SYSCOHADA_LIABILITIES_EQUITY").amount == Money.from_str(
        "25000000", XOF
    )
    assert result.report.node("SYSCOHADA_ASSETS").mapping_provenances == (
        "VALIDATED_CANDIDATE",
    )
    assert "REFERENCE_HINT" not in result.report.node("SYSCOHADA_ASSETS").mapping_provenances
    assert result.report.node("SYSCOHADA_ASSETS").human_validation_required is True
    assert result.validation.is_valid is True
