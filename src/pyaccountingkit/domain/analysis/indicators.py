"""Versioned financial-indicator definitions and value semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyaccountingkit.domain.analysis.errors import InvalidIndicatorDefinitionError
from pyaccountingkit.domain.analysis.formula import AnalysisFormula


class FinancialIndicatorCategory(StrEnum):
    PERFORMANCE = "PERFORMANCE"
    PROFITABILITY = "PROFITABILITY"
    ACTIVITY = "ACTIVITY"
    CASH_GENERATION = "CASH_GENERATION"
    LIQUIDITY = "LIQUIDITY"
    WORKING_CAPITAL = "WORKING_CAPITAL"
    SOLVENCY = "SOLVENCY"
    LEVERAGE = "LEVERAGE"
    CAPITAL_STRUCTURE = "CAPITAL_STRUCTURE"
    EFFICIENCY = "EFFICIENCY"
    GROWTH = "GROWTH"
    CUSTOM = "CUSTOM"


class IndicatorUnit(StrEnum):
    CURRENCY = "CURRENCY"
    PERCENTAGE = "PERCENTAGE"
    RATIO = "RATIO"
    DAYS = "DAYS"
    COUNT = "COUNT"
    INDEX = "INDEX"
    CUSTOM = "CUSTOM"


class DefinitionStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    SUPERSEDED = "SUPERSEDED"


class IndicatorDependencyType(StrEnum):
    STATEMENT_LINE = "STATEMENT_LINE"
    TRIAL_BALANCE_MEASURE = "TRIAL_BALANCE_MEASURE"
    INDICATOR = "INDICATOR"
    EXTERNAL_ANALYTICAL_INPUT = "EXTERNAL_ANALYTICAL_INPUT"


class IndicatorValueStatus(StrEnum):
    CALCULATED = "CALCULATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNDEFINED = "UNDEFINED"
    INDETERMINATE = "INDETERMINATE"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class IndicatorDependency:
    dependency_type: IndicatorDependencyType
    dependency_id: str
    required: bool = True

    def __post_init__(self) -> None:
        if not self.dependency_id.strip():
            raise InvalidIndicatorDefinitionError("dependency id must not be empty")


@dataclass(frozen=True, slots=True)
class FinancialIndicatorDefinition:
    definition_id: str
    code: str
    label: str
    category: FinancialIndicatorCategory
    version: str
    formula: AnalysisFormula
    dependencies: tuple[IndicatorDependency, ...]
    unit: IndicatorUnit
    status: DefinitionStatus = DefinitionStatus.DRAFT
    effective_from: date | None = None
    effective_to: date | None = None
    provenance: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("definition_id", self.definition_id),
            ("code", self.code),
            ("label", self.label),
            ("version", self.version),
        ):
            if not value.strip():
                raise InvalidIndicatorDefinitionError(f"{field_name} must not be empty")
        if self.effective_to is not None and self.effective_from is None:
            raise InvalidIndicatorDefinitionError(
                "effective_to requires effective_from on an indicator definition"
            )
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise InvalidIndicatorDefinitionError("indicator effective dates are inverted")
        dependency_ids = tuple(dependency.dependency_id for dependency in self.dependencies)
        if len(set(dependency_ids)) != len(dependency_ids):
            raise InvalidIndicatorDefinitionError("indicator dependencies must be unique")
        unknown_operands = set(self.formula.operands) - set(dependency_ids)
        if unknown_operands:
            raise InvalidIndicatorDefinitionError(
                "formula references undeclared dependencies: " + ", ".join(sorted(unknown_operands))
            )

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
    "DefinitionStatus",
    "FinancialIndicatorCategory",
    "FinancialIndicatorDefinition",
    "IndicatorDependency",
    "IndicatorDependencyType",
    "IndicatorUnit",
    "IndicatorValueStatus",
]
