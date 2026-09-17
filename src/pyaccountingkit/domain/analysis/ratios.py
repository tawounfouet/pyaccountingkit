"""Versioned financial-ratio definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from pyaccountingkit.domain.analysis.errors import InvalidRatioDefinitionError
from pyaccountingkit.domain.analysis.indicators import DefinitionStatus, IndicatorUnit


class FinancialRatioCategory(StrEnum):
    ACTIVITY = "ACTIVITY"
    PROFITABILITY = "PROFITABILITY"
    LIQUIDITY = "LIQUIDITY"
    SOLVENCY = "SOLVENCY"
    LEVERAGE = "LEVERAGE"
    EFFICIENCY = "EFFICIENCY"
    COVERAGE = "COVERAGE"
    CASH_GENERATION = "CASH_GENERATION"
    CUSTOM = "CUSTOM"


class ZeroDenominatorPolicy(StrEnum):
    UNDEFINED = "UNDEFINED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ZERO_IF_CONFIGURED = "ZERO_IF_CONFIGURED"
    ERROR = "ERROR"


class DayCountPolicy(StrEnum):
    CALENDAR_365 = "CALENDAR_365"
    COMMERCIAL_360 = "COMMERCIAL_360"
    ACTUAL_PERIOD_DAYS = "ACTUAL_PERIOD_DAYS"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class FinancialRatioDefinition:
    definition_id: str
    code: str
    label: str
    category: FinancialRatioCategory
    version: str
    numerator_ref: str
    denominator_ref: str
    scale: Decimal = Decimal("1")
    unit: IndicatorUnit = IndicatorUnit.RATIO
    status: DefinitionStatus = DefinitionStatus.DRAFT
    zero_denominator_policy: ZeroDenominatorPolicy = ZeroDenominatorPolicy.UNDEFINED
    day_count_policy: DayCountPolicy | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    provenance: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("definition_id", self.definition_id),
            ("code", self.code),
            ("label", self.label),
            ("version", self.version),
            ("numerator_ref", self.numerator_ref),
            ("denominator_ref", self.denominator_ref),
        ):
            if not value.strip():
                raise InvalidRatioDefinitionError(f"{field_name} must not be empty")
        if not isinstance(self.scale, Decimal) or not self.scale.is_finite() or self.scale <= 0:
            raise InvalidRatioDefinitionError("ratio scale must be a finite positive Decimal")
        if self.effective_to is not None and self.effective_from is None:
            raise InvalidRatioDefinitionError(
                "effective_to requires effective_from on a ratio definition"
            )
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise InvalidRatioDefinitionError("ratio effective dates are inverted")

    def is_effective_on(self, on_date: date) -> bool:
        if self.effective_from is not None and on_date < self.effective_from:
            return False
        if self.effective_to is not None and on_date > self.effective_to:
            return False
        return True

    @property
    def executable(self) -> bool:
        return self.status is DefinitionStatus.ACTIVE


__all__ = [
    "DayCountPolicy",
    "FinancialRatioCategory",
    "FinancialRatioDefinition",
    "ZeroDenominatorPolicy",
]
