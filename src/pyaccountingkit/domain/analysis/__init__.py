"""Financial-analysis domain model."""

from pyaccountingkit.domain.analysis.analysis_snapshot import AnalysisSnapshot
from pyaccountingkit.domain.analysis.definition_set import AnalysisDefinitionSet
from pyaccountingkit.domain.analysis.diagnostics import (
    DiagnosticEngine,
    DiagnosticOperator,
    DiagnosticRule,
    DiagnosticStatus,
    FinancialDiagnostic,
)
from pyaccountingkit.domain.analysis.engine import (
    FinancialAnalysisEngine,
    FinancialAnalysisRequest,
    FinancialAnalysisResult,
)
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
from pyaccountingkit.domain.analysis.functional_balance import (
    FunctionalBalanceDefinition,
    FunctionalBalanceEngine,
    FunctionalBalanceResult,
)
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
from pyaccountingkit.domain.analysis.trends import MetricTrend, PeriodObservation, TrendDirection
from pyaccountingkit.domain.analysis.values import (
    AnalysisInputValue,
    AnalysisMetricKind,
    CalculationTrace,
    DependencyObservation,
    FinancialIndicatorValue,
    FinancialRatioValue,
    inputs_from_report_snapshot,
)
from pyaccountingkit.domain.analysis.working_capital import WorkingCapitalAnalysis

__all__ = [
    "AnalysisDefinitionSet",
    "AnalysisFormula",
    "AnalysisFormulaOperation",
    "AnalysisInputValue",
    "AnalysisMetricKind",
    "AnalysisSnapshot",
    "CalculationTrace",
    "DayCountPolicy",
    "DefinitionStatus",
    "DependencyObservation",
    "DiagnosticEngine",
    "DiagnosticOperator",
    "DiagnosticRule",
    "DiagnosticStatus",
    "FinancialAnalysisEngine",
    "FinancialAnalysisError",
    "FinancialAnalysisRequest",
    "FinancialAnalysisResult",
    "FinancialAnalysisSource",
    "FinancialAnalysisSourceFreshness",
    "FinancialAnalysisSourceType",
    "FinancialDiagnostic",
    "FinancialIndicatorCategory",
    "FinancialIndicatorDefinition",
    "FinancialIndicatorValue",
    "FinancialRatioCategory",
    "FinancialRatioDefinition",
    "FinancialRatioValue",
    "FunctionalBalanceDefinition",
    "FunctionalBalanceEngine",
    "FunctionalBalanceResult",
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
    "MetricTrend",
    "PeriodObservation",
    "StaleAnalysisSourceError",
    "TrendDirection",
    "UnsupportedAnalysisOperationError",
    "WorkingCapitalAnalysis",
    "ZeroDenominatorPolicy",
    "inputs_from_report_snapshot",
]
