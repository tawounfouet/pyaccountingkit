"""Typed errors for the Financial Analysis bounded context."""

from pyaccountingkit.core.errors import DomainError


class FinancialAnalysisError(DomainError):
    """Root of financial-analysis domain errors."""

    code = "ANALYSIS_ERROR"


class InvalidAnalysisSourceError(FinancialAnalysisError):
    code = "ANALYSIS_INVALID_SOURCE"


class StaleAnalysisSourceError(FinancialAnalysisError):
    code = "ANALYSIS_STALE_SOURCE"


class InvalidIndicatorDefinitionError(FinancialAnalysisError):
    code = "ANALYSIS_INVALID_INDICATOR_DEFINITION"


class InvalidRatioDefinitionError(FinancialAnalysisError):
    code = "ANALYSIS_INVALID_RATIO_DEFINITION"


class IndicatorDependencyCycleError(FinancialAnalysisError):
    code = "ANALYSIS_DEPENDENCY_CYCLE"


class InvalidAnalysisDefinitionSetError(FinancialAnalysisError):
    code = "ANALYSIS_INVALID_DEFINITION_SET"


class UnsupportedAnalysisOperationError(FinancialAnalysisError):
    code = "ANALYSIS_UNSUPPORTED_OPERATION"


class InvalidFunctionalBalanceError(FinancialAnalysisError):
    code = "ANALYSIS_INVALID_FUNCTIONAL_BALANCE"


class InvalidAnalysisSnapshotError(FinancialAnalysisError):
    code = "ANALYSIS_INVALID_SNAPSHOT"


__all__ = [
    "FinancialAnalysisError",
    "IndicatorDependencyCycleError",
    "InvalidAnalysisDefinitionSetError",
    "InvalidAnalysisSnapshotError",
    "InvalidAnalysisSourceError",
    "InvalidFunctionalBalanceError",
    "InvalidIndicatorDefinitionError",
    "InvalidRatioDefinitionError",
    "StaleAnalysisSourceError",
    "UnsupportedAnalysisOperationError",
]
