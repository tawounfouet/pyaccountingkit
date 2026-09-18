"""Immutable analytical inputs, values and calculation traces."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from pyaccountingkit.domain.analysis.errors import InvalidAnalysisSourceError
from pyaccountingkit.domain.analysis.indicators import IndicatorUnit, IndicatorValueStatus
from pyaccountingkit.domain.reporting.report_snapshot import ReportSnapshot


class AnalysisMetricKind(StrEnum):
    INDICATOR = "INDICATOR"
    RATIO = "RATIO"


@dataclass(frozen=True, slots=True)
class AnalysisInputValue:
    key: str
    value: Decimal
    source_ref: str

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise InvalidAnalysisSourceError("analysis input key must not be empty")
        if not self.source_ref.strip():
            raise InvalidAnalysisSourceError("analysis input source_ref must not be empty")
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise InvalidAnalysisSourceError("analysis input value must be a finite Decimal")


@dataclass(frozen=True, slots=True)
class DependencyObservation:
    ref: str
    status: IndicatorValueStatus
    value: Decimal | None

    def __post_init__(self) -> None:
        if not self.ref.strip():
            raise ValueError("dependency observation ref must not be empty")
        if self.status is IndicatorValueStatus.CALCULATED:
            if self.value is None or not self.value.is_finite():
                raise ValueError("calculated dependency must carry a finite Decimal")
        elif self.value is not None:
            raise ValueError("non-calculated dependency must not carry a value")


@dataclass(frozen=True, slots=True)
class FinancialIndicatorValue:
    definition_id: str
    definition_version: str
    code: str
    value: Decimal | None
    unit: IndicatorUnit
    status: IndicatorValueStatus
    source_refs: tuple[str, ...]
    dependencies: tuple[DependencyObservation, ...]
    message: str | None = None
    checksum: str = field(init=False)

    def __post_init__(self) -> None:
        self._validate()
        object.__setattr__(self, "checksum", self._compute_checksum())

    def _validate(self) -> None:
        if not self.definition_id.strip() or not self.definition_version.strip() or not self.code.strip():
            raise ValueError("indicator value identity fields must not be empty")
        if self.status is IndicatorValueStatus.CALCULATED:
            if self.value is None or not self.value.is_finite():
                raise ValueError("calculated indicator must carry a finite Decimal")
        elif self.value is not None:
            raise ValueError("non-calculated indicator must not carry a value")

    def _compute_checksum(self) -> str:
        payload = {
            "definition_id": self.definition_id,
            "definition_version": self.definition_version,
            "code": self.code,
            "value": str(self.value) if self.value is not None else None,
            "unit": self.unit.value,
            "status": self.status.value,
            "source_refs": list(self.source_refs),
            "dependencies": [
                {
                    "ref": item.ref,
                    "status": item.status.value,
                    "value": str(item.value) if item.value is not None else None,
                }
                for item in self.dependencies
            ],
            "message": self.message,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class FinancialRatioValue:
    definition_id: str
    definition_version: str
    code: str
    value: Decimal | None
    unit: IndicatorUnit
    status: IndicatorValueStatus
    numerator_value: Decimal | None
    denominator_value: Decimal | None
    source_refs: tuple[str, ...]
    message: str | None = None
    checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.definition_id.strip() or not self.definition_version.strip() or not self.code.strip():
            raise ValueError("ratio value identity fields must not be empty")
        if self.status is IndicatorValueStatus.CALCULATED:
            if self.value is None or not self.value.is_finite():
                raise ValueError("calculated ratio must carry a finite Decimal")
        elif self.value is not None:
            raise ValueError("non-calculated ratio must not carry a value")
        object.__setattr__(self, "checksum", self._compute_checksum())

    def _compute_checksum(self) -> str:
        payload = {
            "definition_id": self.definition_id,
            "definition_version": self.definition_version,
            "code": self.code,
            "value": str(self.value) if self.value is not None else None,
            "unit": self.unit.value,
            "status": self.status.value,
            "numerator": str(self.numerator_value) if self.numerator_value is not None else None,
            "denominator": (
                str(self.denominator_value) if self.denominator_value is not None else None
            ),
            "source_refs": list(self.source_refs),
            "message": self.message,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class CalculationTrace:
    metric_kind: AnalysisMetricKind
    metric_code: str
    definition_id: str
    definition_version: str
    operation: str
    dependencies: tuple[DependencyObservation, ...]
    status: IndicatorValueStatus
    result_value: Decimal | None
    checksum: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.metric_code.strip() or not self.definition_id.strip():
            raise ValueError("calculation trace identity fields must not be empty")
        object.__setattr__(self, "checksum", self._compute_checksum())

    def _compute_checksum(self) -> str:
        payload = {
            "metric_kind": self.metric_kind.value,
            "metric_code": self.metric_code,
            "definition_id": self.definition_id,
            "definition_version": self.definition_version,
            "operation": self.operation,
            "dependencies": [
                {
                    "ref": item.ref,
                    "status": item.status.value,
                    "value": str(item.value) if item.value is not None else None,
                }
                for item in self.dependencies
            ],
            "status": self.status.value,
            "result_value": str(self.result_value) if self.result_value is not None else None,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def inputs_from_report_snapshot(snapshot: ReportSnapshot) -> tuple[AnalysisInputValue, ...]:
    return tuple(
        AnalysisInputValue(
            key=line.code,
            value=line.amount.amount,
            source_ref=f"{snapshot.snapshot_id}:{line.code}",
        )
        for line in snapshot.lines
    )


__all__ = [
    "AnalysisInputValue",
    "AnalysisMetricKind",
    "CalculationTrace",
    "DependencyObservation",
    "FinancialIndicatorValue",
    "FinancialRatioValue",
    "inputs_from_report_snapshot",
]
