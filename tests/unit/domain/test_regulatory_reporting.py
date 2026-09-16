"""LOT-17 qualification for regulatory reporting projection and validation."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from pyaccountingkit.adapters.in_memory.reference_reporting_model_provider import (
    InMemoryReferenceReportingModelProvider,
)
from pyaccountingkit.application.reporting.regulatory_reporting_service import (
    RegulatoryReportingService,
)
from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.errors import EntityScopeMismatchError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.errors import RegulatoryReportingError
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
from pyaccountingkit.domain.reporting.regulatory_validation import RegulatoryValidationStatus
from pyaccountingkit.domain.reporting.report_snapshot import (
    ReportSnapshot,
    ReportSnapshotLine,
    ReportSnapshotStatus,
)
from pyaccountingkit.domain.reporting.statement_definition import FinancialStatementType

ENTITY = EntityId("entity-a")
OTHER_ENTITY = EntityId("entity-b")
AS_OF = date(2026, 12, 31)


def _snapshot(*, status: ReportSnapshotStatus = ReportSnapshotStatus.PUBLISHED) -> ReportSnapshot:
    return ReportSnapshot(
        snapshot_id="financial-snapshot-1",
        accounting_entity_id=ENTITY,
        report_type=FinancialStatementType.BALANCE_SHEET,
        source_period_id="FY2026",
        source_checksum="source-checksum",
        statement_definition_id="bs-pcg",
        statement_definition_version="1",
        statement_definition_checksum="statement-checksum",
        mapping_set_id="statement-map-1",
        mapping_set_version="1",
        mapping_set_checksum="statement-map-checksum",
        result_checksum="financial-result-checksum",
        as_of=AS_OF,
        created_at=datetime(2026, 12, 31, tzinfo=UTC),
        status=status,
        lines=(
            ReportSnapshotLine(
                code="FS_ASSETS",
                label="Assets",
                amount=Money.from_str("100", EUR),
                comparative_amount=Money.from_str("80", EUR),
            ),
        ),
        checksum="sealed-financial-snapshot-checksum",
    )


def _model() -> ReferenceReportingModel:
    return ReferenceReportingModel(
        model_id="pcg-bs-model",
        model_code="BALANCE_SHEET",
        framework="PCG",
        edition="2026",
        reference_snapshot_id="ref-pcg-2026",
        reference_snapshot_checksum="a" * 64,
        nodes=(
            ReferenceReportingNode(
                node_id="assets",
                code="REG_ASSETS",
                label="Regulatory assets",
                node_type=ReferenceReportingNodeType.TOTAL,
                order=1,
                required=True,
                human_validation_required=True,
                account_hints_executable=False,
                account_hints=("1*",),
            ),
        ),
    )


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


def _mapping_set(
    *,
    entity: EntityId = ENTITY,
    mappings: tuple[RegulatoryStatementMapping, ...] | None = None,
) -> RegulatoryMappingSet:
    if mappings is None:
        mappings = (
            RegulatoryStatementMapping(
                mapping_id="m1",
                statement_line_code="FS_ASSETS",
                reference_node_id="assets",
                allocation=Decimal("1"),
                status=RegulatoryMappingStatus.VALIDATED,
                provenance=RegulatoryMappingProvenance.MANUAL,
                effective_from=date(2026, 1, 1),
            ),
        )
    return RegulatoryMappingSet(
        mapping_set_id="reg-map-1",
        accounting_entity_id=entity,
        profile_id="pcg-profile",
        reference_model_id="pcg-bs-model",
        version="1",
        status=RegulatoryMappingSetStatus.ACTIVE,
        mappings=mappings,
        effective_from=date(2026, 1, 1),
    )


def _service() -> RegulatoryReportingService:
    return RegulatoryReportingService(InMemoryReferenceReportingModelProvider((_model(),)))


def test_reporting_service_projects_published_snapshot_without_recalculating_ledger() -> None:
    result = _service().build(
        snapshot=_snapshot(),
        profile=_profile(),
        mapping_set=_mapping_set(),
        model_code="BALANCE_SHEET",
    )

    node = result.report.node("REG_ASSETS")
    assert node.amount == Money.from_str("100", EUR)
    assert node.comparative_amount == Money.from_str("80", EUR)
    assert node.source_statement_lines == ("FS_ASSETS",)
    assert node.mapping_provenances == ("MANUAL",)
    assert node.human_validation_required is True
    assert node.account_hints_executable is False
    assert result.report.source_report_checksum == "sealed-financial-snapshot-checksum"
    assert result.validation.is_valid is True
    assert all(
        validation.status is RegulatoryValidationStatus.PASS
        for validation in result.validation.results
    )


def test_unmapped_required_node_is_reported_as_blocking_validation_failure() -> None:
    result = _service().build(
        snapshot=_snapshot(),
        profile=_profile(),
        mapping_set=_mapping_set(mappings=()),
        model_code="BALANCE_SHEET",
    )

    assert result.validation.has_blocking_failures is True
    assert result.validation.results[0].rule_id == "REQUIRED_MAPPING:REG_ASSETS"
    assert result.validation.results[0].status is RegulatoryValidationStatus.FAIL


def test_regulatory_reporting_requires_published_financial_snapshot() -> None:
    with pytest.raises(RegulatoryReportingError, match="published"):
        _service().build(
            snapshot=_snapshot(status=ReportSnapshotStatus.DRAFT),
            profile=_profile(),
            mapping_set=_mapping_set(),
            model_code="BALANCE_SHEET",
        )


def test_regulatory_reporting_rejects_cross_entity_mapping_set() -> None:
    with pytest.raises(EntityScopeMismatchError):
        _service().build(
            snapshot=_snapshot(),
            profile=_profile(),
            mapping_set=_mapping_set(entity=OTHER_ENTITY),
            model_code="BALANCE_SHEET",
        )


def test_regulatory_report_checksum_is_deterministic() -> None:
    first = _service().build(
        snapshot=_snapshot(),
        profile=_profile(),
        mapping_set=_mapping_set(),
        model_code="BALANCE_SHEET",
    )
    second = _service().build(
        snapshot=_snapshot(),
        profile=_profile(),
        mapping_set=_mapping_set(),
        model_code="BALANCE_SHEET",
    )

    assert first.report.checksum == second.report.checksum
    assert first.validation.checksum == second.validation.checksum
