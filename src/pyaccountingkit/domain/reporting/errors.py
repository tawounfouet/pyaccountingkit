"""Financial-reporting domain errors with stable machine-readable codes."""

from __future__ import annotations

from pyaccountingkit.core.errors import DomainError


class ReportingError(DomainError):
    code = "REPORTING_ERROR"


class InvalidStatementDefinitionError(ReportingError):
    code = "REPORTING_INVALID_DEFINITION"


class FormulaCycleError(InvalidStatementDefinitionError):
    code = "REPORTING_FORMULA_CYCLE"


class StatementMappingError(ReportingError):
    code = "REPORTING_MAPPING_ERROR"


class NonExecutableStatementMappingError(StatementMappingError):
    code = "REPORTING_MAPPING_NOT_EXECUTABLE"


class StatementSourceError(ReportingError):
    code = "REPORTING_INVALID_SOURCE"


class StatementControlError(ReportingError):
    code = "REPORTING_CONTROL_FAILED"


__all__ = [
    "FormulaCycleError",
    "InvalidStatementDefinitionError",
    "NonExecutableStatementMappingError",
    "ReportingError",
    "StatementControlError",
    "StatementMappingError",
    "StatementSourceError",
]
