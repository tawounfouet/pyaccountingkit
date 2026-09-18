"""Explicit policy-driven financial diagnostics."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from pyaccountingkit.domain.analysis.indicators import DefinitionStatus, IndicatorValueStatus


class DiagnosticOperator(StrEnum):
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    EQ = "EQ"
    NE = "NE"


class DiagnosticStatus(StrEnum):
    MATCHED = "MATCHED"
    NOT_MATCHED = "NOT_MATCHED"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True, slots=True)
class DiagnosticRule:
    rule_id: str
    version: str
    metric_code: str
    operator: DiagnosticOperator
    threshold: Decimal
    label: str
    message: str
    status: DefinitionStatus = DefinitionStatus.DRAFT

    def __post_init__(self) -> None:
        if any(
            not value.strip()
            for value in (self.rule_id, self.version, self.metric_code, self.label, self.message)
        ):
            raise ValueError("diagnostic rule identity/text fields must not be empty")
        if not isinstance(self.threshold, Decimal) or not self.threshold.is_finite():
            raise ValueError("diagnostic threshold must be a finite Decimal")


@dataclass(frozen=True, slots=True)
class FinancialDiagnostic:
    rule_id: str
    rule_version: str
    metric_code: str
    metric_value: Decimal | None
    status: DiagnosticStatus
    label: str | None
    message: str | None
    checksum: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "checksum", self._compute_checksum())

    def _compute_checksum(self) -> str:
        payload = {
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "metric_code": self.metric_code,
            "metric_value": str(self.metric_value) if self.metric_value is not None else None,
            "status": self.status.value,
            "label": self.label,
            "message": self.message,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class DiagnosticEngine:
    def evaluate(
        self,
        *,
        rule: DiagnosticRule,
        metric_value: Decimal | None,
        metric_status: IndicatorValueStatus,
    ) -> FinancialDiagnostic:
        if rule.status is not DefinitionStatus.ACTIVE:
            raise ValueError("diagnostic rule must be ACTIVE")
        if metric_status is not IndicatorValueStatus.CALCULATED or metric_value is None:
            return FinancialDiagnostic(
                rule_id=rule.rule_id,
                rule_version=rule.version,
                metric_code=rule.metric_code,
                metric_value=None,
                status=DiagnosticStatus.INDETERMINATE,
                label=None,
                message="metric is not calculated",
            )
        matched = self._matches(metric_value, rule.operator, rule.threshold)
        return FinancialDiagnostic(
            rule_id=rule.rule_id,
            rule_version=rule.version,
            metric_code=rule.metric_code,
            metric_value=metric_value,
            status=DiagnosticStatus.MATCHED if matched else DiagnosticStatus.NOT_MATCHED,
            label=rule.label if matched else None,
            message=rule.message if matched else None,
        )

    @staticmethod
    def _matches(value: Decimal, operator: DiagnosticOperator, threshold: Decimal) -> bool:
        if operator is DiagnosticOperator.GT:
            return value > threshold
        if operator is DiagnosticOperator.GTE:
            return value >= threshold
        if operator is DiagnosticOperator.LT:
            return value < threshold
        if operator is DiagnosticOperator.LTE:
            return value <= threshold
        if operator is DiagnosticOperator.EQ:
            return value == threshold
        if operator is DiagnosticOperator.NE:
            return value != threshold
        raise ValueError(f"unsupported diagnostic operator {operator!r}")


__all__ = [
    "DiagnosticEngine",
    "DiagnosticOperator",
    "DiagnosticRule",
    "DiagnosticStatus",
    "FinancialDiagnostic",
]
