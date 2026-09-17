"""Financial-analysis domain model."""

from pyaccountingkit.domain.analysis.definition_set import AnalysisDefinitionSet
from pyaccountingkit.domain.analysis.errors import (
    FinancialAnalysisError,
    IndicatorDependencyCycleError,
    InvalidAnalysisDefinitionSetError,
    InvalidAnalysisSnapshotError,
    InvalidAnalysisSourceError,
    InvalidFunctionalBalanceError,
    InvalidIndicatorDefinitionError,
    InvalidRatioDefinitionError,
    StaleAnalysisSourceError,
    UnsupportedAnalysisOperationError,
)
from pyaccountingkit.domain.analysis.formula import AnalysisFormula, AnalysisFormulaOperation
from pyaccountingkit.domain.analysis.indicators import (
    DefinitionStatus,
    FinancialIndicatorCategory,
    FinancialIndicatorDefinition,
    IndicatorDependency,
    IndicatorDependencyType,
    IndicatorUnit,
    IndicatorValueStatus,
)
from pyaccountingkit.domain.analysis.ratios import (
    DayCountPolicy,
    FinancialRatioCategory,
    FinancialRatioDefinition,
    ZeroDenominatorPolicy,
)
from pyaccountingkit.domain.analysis.source import (
    FinancialAnalysisSource,
    FinancialAnalysisSourceFreshness,
    FinancialAnalysisSourceType,
)

__all__ = [
    "AnalysisDefinitionSet",
    "AnalysisFormula",
    "AnalysisFormulaOperation",
    "DayCountPolicy",
    "DefinitionStatus",
    "FinancialAnalysisError",
    "FinancialAnalysisSource",
    "FinancialAnalysisSourceFreshness",
    "FinancialAnalysisSourceType",
    "FinancialIndicatorCategory",
    "FinancialIndicatorDefinition",
    "FinancialRatioCategory",
    "FinancialRatioDefinition",
    "IndicatorDependency",
    "IndicatorDependencyCycleError",
    "IndicatorDependencyType",
    "IndicatorUnit",
    "IndicatorValueStatus",
    "InvalidAnalysisDefinitionSetError",
    "InvalidAnalysisSnapshotError",
    "InvalidAnalysisSourceError",
    "InvalidFunctionalBalanceError",
    "InvalidIndicatorDefinitionError",
    "InvalidRatioDefinitionError",
    "StaleAnalysisSourceError",
    "UnsupportedAnalysisOperationError",
    "ZeroDenominatorPolicy",
]
