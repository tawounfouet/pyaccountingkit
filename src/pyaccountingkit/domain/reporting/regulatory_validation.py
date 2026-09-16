"""Deterministic regulatory-report validation results and engine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from pyaccountingkit.domain.reporting.errors import RegulatoryReferenceMismatchError
from pyaccountingkit.domain.reporting.reference_reporting_model import (
    ReferenceReportingModel,
    ReferenceReportingValueType,
)
from pyaccountingkit.domain.reporting.regulatory_report import RegulatoryReport


class RegulatoryValidationSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    BLOCKING = "BLOCKING"


class RegulatoryValidationStatus(StrEnum):
    PASS = "PASS"  # nosec B105 - regulatory validation outcome, not a credential
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class RegulatoryValidationResult:
    rule_id: str
    severity: RegulatoryValidationSeverity
    status: RegulatoryValidationStatus
    message: str
    node_id: str | None = None


@dataclass(frozen=True, slots=True)
class RegulatoryValidationReport:
    results: tuple[RegulatoryValidationResult, ...]
    checksum: str

    @classmethod
    def build(
        cls,
        results: tuple[RegulatoryValidationResult, ...],
    ) -> RegulatoryValidationReport:
        payload = [
            {
                "rule_id": result.rule_id,
                "severity": result.severity.value,
                "status": result.status.value,
                "message": result.message,
                "node_id": result.node_id,
            }
            for result in results
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return cls(results=results, checksum=hashlib.sha256(encoded).hexdigest())

    @property
    def has_blocking_failures(self) -> bool:
        return any(
            result.status is RegulatoryValidationStatus.FAIL
            and result.severity is RegulatoryValidationSeverity.BLOCKING
            for result in self.results
        )

    @property
    def is_valid(self) -> bool:
        return not self.has_blocking_failures


class RegulatoryValidationEngine:
    """Validate regulatory projections without mutating or recalculating accounting."""

    def validate(
        self,
        report: RegulatoryReport,
        model: ReferenceReportingModel,
    ) -> RegulatoryValidationReport:
        if (
            report.reference_model_id != model.model_id
            or report.reference_model_checksum != model.checksum
            or report.reference_snapshot_id != model.reference_snapshot_id
            or report.reference_snapshot_checksum != model.reference_snapshot_checksum
        ):
            raise RegulatoryReferenceMismatchError(
                "regulatory report and reference reporting model coordinates differ"
            )

        values = {node.node_id: node for node in report.nodes}
        results: list[RegulatoryValidationResult] = []
        for node in model.ordered_nodes:
            value = values[node.node_id]
            if node.required and node.value_type is ReferenceReportingValueType.MONEY:
                mapped = bool(value.source_statement_lines)
                results.append(
                    RegulatoryValidationResult(
                        rule_id=f"REQUIRED_MAPPING:{node.code}",
                        severity=RegulatoryValidationSeverity.BLOCKING,
                        status=(
                            RegulatoryValidationStatus.PASS
                            if mapped
                            else RegulatoryValidationStatus.FAIL
                        ),
                        message=(
                            "required regulatory node has an explicit validated mapping"
                            if mapped
                            else "required regulatory node has no validated mapping"
                        ),
                        node_id=node.node_id,
                    )
                )

            if node.human_validation_required:
                preserved = value.human_validation_required
                results.append(
                    RegulatoryValidationResult(
                        rule_id=f"HUMAN_VALIDATION_PRESERVED:{node.code}",
                        severity=RegulatoryValidationSeverity.BLOCKING,
                        status=(
                            RegulatoryValidationStatus.PASS
                            if preserved
                            else RegulatoryValidationStatus.FAIL
                        ),
                        message="human-validation requirement must be preserved in the report",
                        node_id=node.node_id,
                    )
                )

            if node.account_hints:
                hint_executed = "REFERENCE_HINT" in value.mapping_provenances
                results.append(
                    RegulatoryValidationResult(
                        rule_id=f"ACCOUNT_HINT_EXECUTION_SAFETY:{node.code}",
                        severity=RegulatoryValidationSeverity.BLOCKING,
                        status=(
                            RegulatoryValidationStatus.FAIL
                            if hint_executed
                            else RegulatoryValidationStatus.PASS
                        ),
                        message=(
                            "reference account hints must not execute as validated mappings"
                        ),
                        node_id=node.node_id,
                    )
                )

        return RegulatoryValidationReport.build(tuple(results))


__all__ = [
    "RegulatoryValidationEngine",
    "RegulatoryValidationReport",
    "RegulatoryValidationResult",
    "RegulatoryValidationSeverity",
    "RegulatoryValidationStatus",
]
