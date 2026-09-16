"""Financial and regulatory reporting domain errors with stable codes."""

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


class RegulatoryReportingError(ReportingError):
    code = "REGULATORY_REPORTING_ERROR"


class RegulatoryProfileError(RegulatoryReportingError):
    code = "REGULATORY_PROFILE_ERROR"


class RegulatoryProfileNotActiveError(RegulatoryProfileError):
    code = "REGULATORY_PROFILE_NOT_ACTIVE"


class RegulatoryProfileNotEffectiveError(RegulatoryProfileError):
    code = "REGULATORY_PROFILE_NOT_EFFECTIVE"


class RegulatoryReferenceMismatchError(RegulatoryReportingError):
    code = "REGULATORY_REFERENCE_MISMATCH"


class RegulatoryModelNotFoundError(RegulatoryReportingError):
    code = "REGULATORY_MODEL_NOT_FOUND"


class RegulatoryMappingError(RegulatoryReportingError):
    code = "REGULATORY_MAPPING_ERROR"


class NonExecutableRegulatoryMappingError(RegulatoryMappingError):
    code = "REGULATORY_MAPPING_NOT_EXECUTABLE"


class IncompleteRegulatoryMappingError(RegulatoryMappingError):
    code = "REGULATORY_MAPPING_INCOMPLETE"


class RegulatoryValidationError(RegulatoryReportingError):
    code = "REGULATORY_VALIDATION_FAILED"


class RegulatoryExportError(RegulatoryReportingError):
    code = "REGULATORY_EXPORT_FAILED"


class RegulatoryExportIncompatibleError(RegulatoryExportError):
    code = "REGULATORY_EXPORT_INCOMPATIBLE"


class RegulatoryEvidenceMismatchError(RegulatoryReportingError):
    code = "REGULATORY_EVIDENCE_MISMATCH"


class RegulatoryUpgradeReviewRequiredError(RegulatoryReportingError):
    code = "REGULATORY_UPGRADE_REVIEW_REQUIRED"


__all__ = [
    "FormulaCycleError",
    "IncompleteRegulatoryMappingError",
    "InvalidStatementDefinitionError",
    "NonExecutableRegulatoryMappingError",
    "NonExecutableStatementMappingError",
    "RegulatoryEvidenceMismatchError",
    "RegulatoryExportError",
    "RegulatoryExportIncompatibleError",
    "RegulatoryMappingError",
    "RegulatoryModelNotFoundError",
    "RegulatoryProfileError",
    "RegulatoryProfileNotActiveError",
    "RegulatoryProfileNotEffectiveError",
    "RegulatoryReferenceMismatchError",
    "RegulatoryReportingError",
    "RegulatoryUpgradeReviewRequiredError",
    "RegulatoryValidationError",
    "ReportingError",
    "StatementControlError",
    "StatementMappingError",
    "StatementSourceError",
]
