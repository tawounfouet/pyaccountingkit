"""Application service building regulatory reports from sealed financial snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.errors import (
    RegulatoryMappingError,
    RegulatoryReferenceMismatchError,
    RegulatoryReportingError,
)
from pyaccountingkit.domain.reporting.reference_reporting_model import (
    ReferenceReportingModel,
    ReferenceReportingValueType,
)
from pyaccountingkit.domain.reporting.regulatory_mapping import RegulatoryMappingSet
from pyaccountingkit.domain.reporting.regulatory_profile import RegulatoryReportingProfile
from pyaccountingkit.domain.reporting.regulatory_report import (
    RegulatoryNodeValue,
    RegulatoryReport,
)
from pyaccountingkit.domain.reporting.regulatory_validation import (
    RegulatoryValidationEngine,
    RegulatoryValidationReport,
)
from pyaccountingkit.domain.reporting.report_snapshot import (
    ReportSnapshot,
    ReportSnapshotStatus,
)
from pyaccountingkit.ports.regulatory_reporting import ReferenceReportingModelProviderProtocol


@dataclass(frozen=True, slots=True)
class RegulatoryReportingResult:
    report: RegulatoryReport
    validation: RegulatoryValidationReport


class RegulatoryReportingService:
    """Project one published financial snapshot into a regulatory model."""

    def __init__(
        self,
        model_provider: ReferenceReportingModelProviderProtocol,
        validation_engine: RegulatoryValidationEngine | None = None,
    ) -> None:
        self._model_provider = model_provider
        self._validation_engine = validation_engine or RegulatoryValidationEngine()

    def build(
        self,
        *,
        snapshot: ReportSnapshot,
        profile: RegulatoryReportingProfile,
        mapping_set: RegulatoryMappingSet,
        model_code: str,
    ) -> RegulatoryReportingResult:
        if snapshot.status is not ReportSnapshotStatus.PUBLISHED:
            raise RegulatoryReportingError(
                "regulatory reporting requires a published financial report snapshot"
            )

        model = self._model_provider.get_reporting_model(
            reference_snapshot_id=profile.reference_snapshot_id,
            framework=profile.framework,
            edition=profile.edition,
            model_code=model_code,
        )
        profile.assert_executable(
            entity_id=snapshot.accounting_entity_id,
            as_of=snapshot.as_of,
            reference_snapshot_id=model.reference_snapshot_id,
            reference_snapshot_checksum=model.reference_snapshot_checksum,
        )
        self._validate_coordinates(
            snapshot=snapshot,
            profile=profile,
            mapping_set=mapping_set,
            model=model,
        )
        mapping_set.assert_allocations(as_of=snapshot.as_of)

        source_lines = {line.code: line for line in snapshot.lines}
        if not source_lines:
            raise RegulatoryReportingError("regulatory reporting source has no statement lines")
        currency = next(iter(source_lines.values())).amount.currency

        amounts = {
            node.node_id: Money.zero(currency)
            for node in model.nodes
            if node.value_type is ReferenceReportingValueType.MONEY
        }
        comparative_amounts = {
            node.node_id: Money.zero(currency)
            for node in model.nodes
            if node.value_type is ReferenceReportingValueType.MONEY
        }
        comparative_complete = {node.node_id: True for node in model.nodes}
        source_codes: dict[str, list[str]] = {node.node_id: [] for node in model.nodes}
        mapping_ids: dict[str, list[str]] = {node.node_id: [] for node in model.nodes}
        provenances: dict[str, list[str]] = {node.node_id: [] for node in model.nodes}

        for mapping in sorted(mapping_set.mappings, key=lambda item: item.mapping_id):
            if not mapping.effective_on(snapshot.as_of) or not mapping.is_executable:
                continue
            try:
                source = source_lines[mapping.statement_line_code]
            except KeyError as exc:
                raise RegulatoryMappingError(
                    f"regulatory mapping {mapping.mapping_id!r} references unknown statement "
                    f"line {mapping.statement_line_code!r}"
                ) from exc
            try:
                target = model.node_by_id(mapping.reference_node_id)
            except KeyError as exc:
                raise RegulatoryMappingError(
                    f"regulatory mapping {mapping.mapping_id!r} references unknown model node "
                    f"{mapping.reference_node_id!r}"
                ) from exc
            if target.value_type is not ReferenceReportingValueType.MONEY:
                raise RegulatoryMappingError(
                    f"monetary statement line {source.code!r} cannot map to non-money node "
                    f"{target.code!r}"
                )

            amounts[target.node_id] = amounts[target.node_id] + source.amount * mapping.allocation
            if source.comparative_amount is None:
                comparative_complete[target.node_id] = False
            else:
                comparative_amounts[target.node_id] = (
                    comparative_amounts[target.node_id]
                    + source.comparative_amount * mapping.allocation
                )
            source_codes[target.node_id].append(source.code)
            mapping_ids[target.node_id].append(mapping.mapping_id)
            provenances[target.node_id].append(mapping.provenance.value)

        nodes = tuple(
            RegulatoryNodeValue(
                node_id=node.node_id,
                code=node.code,
                label=node.label,
                value_type=node.value_type,
                amount=(amounts[node.node_id] if node.node_id in amounts else None),
                comparative_amount=(
                    comparative_amounts[node.node_id]
                    if node.node_id in comparative_amounts
                    and source_codes[node.node_id]
                    and comparative_complete[node.node_id]
                    else None
                ),
                source_statement_lines=tuple(sorted(source_codes[node.node_id])),
                mapping_ids=tuple(sorted(mapping_ids[node.node_id])),
                mapping_provenances=tuple(sorted(provenances[node.node_id])),
                human_validation_required=node.human_validation_required,
                account_hints_executable=node.account_hints_executable,
            )
            for node in model.ordered_nodes
        )
        report = RegulatoryReport.build(
            accounting_entity_id=snapshot.accounting_entity_id,
            profile_id=profile.profile_id,
            profile_version=profile.version,
            profile_checksum=profile.checksum,
            framework=profile.framework,
            jurisdiction=profile.jurisdiction,
            edition=profile.edition,
            reference_snapshot_id=model.reference_snapshot_id,
            reference_snapshot_checksum=model.reference_snapshot_checksum,
            reference_model_id=model.model_id,
            reference_model_checksum=model.checksum,
            source_report_snapshot_id=snapshot.snapshot_id,
            source_report_checksum=snapshot.checksum,
            regulatory_mapping_set_id=mapping_set.mapping_set_id,
            regulatory_mapping_set_version=mapping_set.version,
            regulatory_mapping_set_checksum=mapping_set.checksum,
            as_of=snapshot.as_of,
            nodes=nodes,
        )
        validation = self._validation_engine.validate(report, model)
        return RegulatoryReportingResult(report=report, validation=validation)

    @staticmethod
    def _validate_coordinates(
        *,
        snapshot: ReportSnapshot,
        profile: RegulatoryReportingProfile,
        mapping_set: RegulatoryMappingSet,
        model: ReferenceReportingModel,
    ) -> None:
        require_same_entity(
            snapshot.accounting_entity_id,
            mapping_set.accounting_entity_id,
            resource="regulatory mapping set",
        )
        if mapping_set.profile_id != profile.profile_id:
            raise RegulatoryMappingError("regulatory mapping set targets a different profile")
        if mapping_set.mapping_set_id != profile.regulatory_mapping_set_id:
            raise RegulatoryMappingError(
                "regulatory profile pins a different regulatory mapping set"
            )
        if mapping_set.reference_model_id != model.model_id:
            raise RegulatoryMappingError(
                "regulatory mapping set targets a different reference reporting model"
            )
        if snapshot.statement_definition_id not in profile.financial_statement_definition_ids:
            raise RegulatoryMappingError(
                "financial report snapshot definition is outside the regulatory profile scope"
            )
        if (
            model.framework != profile.framework
            or model.edition != profile.edition
            or model.reference_snapshot_id != profile.reference_snapshot_id
            or model.reference_snapshot_checksum != profile.reference_snapshot_checksum
        ):
            raise RegulatoryReferenceMismatchError(
                "regulatory profile and reference reporting model coordinates differ"
            )


__all__ = ["RegulatoryReportingResult", "RegulatoryReportingService"]
