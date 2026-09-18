#!/usr/bin/env python3
"""Generate PUBLIC_ERROR_CODES.json deterministically from canonical error classes."""

from __future__ import annotations

import importlib
from typeguard import TypeCheckError  # type: ignore[import-not-found]  # pragma: no cover

from manifest_generation import parse_check_flag, project_version, write_or_check

_FILENAME = "PUBLIC_ERROR_CODES.json"
_ERROR_MODULES = (
    "pyaccountingkit.core.errors",
    "pyaccountingkit.domain.reporting.errors",
    "pyaccountingkit.domain.subledgers.errors",
    "pyaccountingkit.domain.analysis.errors",
    "pyaccountingkit.public.errors",
)
_PUBLIC_ERROR_CLASS_NAMES = [
    "AccountRoleResolutionError",
    "AccountingImportError",
    "AdapterContractMismatchError",
    "AllocationConcurrencyConflictError",
    "AlreadyReversedError",
    "AmbiguousAccountRoleError",
    "AmbiguousChartVersionError",
    "AmbiguousControlAccountError",
    "AmbiguousPolicyResolutionError",
    "AuxiliaryPolicyNotActiveError",
    "AuxiliaryPolicyNotEffectiveError",
    "ChartVersionNotFoundError",
    "ControlAccountNotConfiguredError",
    "DateOutsidePeriodError",
    "DebitAndCreditSetError",
    "DueItemOverAllocationError",
    "EmptyEntryError",
    "EntityScopeMismatchError",
    "EntryAlreadyPostedError",
    "EntryNotFoundError",
    "EntryNotPostedError",
    "FinancialAnalysisError",
    "FormulaCycleError",
    "IdempotencyReplayError",
    "InactiveAccountError",
    "InactiveJournalError",
    "IncompleteRegulatoryMappingError",
    "IndicatorDependencyCycleError",
    "InvalidAccountCodeError",
    "InvalidAgingPolicyError",
    "InvalidAgingSourceError",
    "InvalidAnalysisDefinitionSetError",
    "InvalidAnalysisSnapshotError",
    "InvalidAnalysisSourceError",
    "InvalidDueItemError",
    "InvalidFunctionalBalanceError",
    "InvalidImportPlanError",
    "InvalidImportTransitionError",
    "InvalidIndicatorDefinitionError",
    "InvalidMatchingError",
    "InvalidPaymentTermError",
    "InvalidRatioDefinitionError",
    "InvalidSettlementError",
    "InvalidStatementDefinitionError",
    "InvalidSubledgerConfigurationError",
    "InvalidSubledgerItemError",
    "JournalNotFoundError",
    "MatchOverAllocationError",
    "NegativeAmountError",
    "NonExecutableMatchingError",
    "NonExecutableRegulatoryMappingError",
    "NonExecutableStatementMappingError",
    "NonPostableAccountError",
    "OptionalDependencyMissingError",
    "PeriodClosedError",
    "PeriodNotFoundError",
    "PolicyNotFoundError",
    "PolicyReferenceMismatchError",
    "PolicySetNotActiveError",
    "PolicySetNotEffectiveError",
    "PublicBoundaryViolationError",
    "PublicOperationUnavailableError",
    "PublicValidationError",
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
    "RevisionConflictError",
    "SettlementAlreadyReversedError",
    "SettlementNotAccountingEffectiveError",
    "SettlementOverAllocationError",
    "StaleAnalysisSourceError",
    "StaleImportPlanError",
    "StatementControlError",
    "StatementMappingError",
    "StatementSourceError",
    "SubledgerAccountingLinkError",
    "SubledgerError",
    "SubledgerReconciliationError",
    "UnbalancedEntryError",
    "UnbalancedProposalError",
    "UnknownAccountError",
    "UnsupportedAnalysisOperationError",
    "WriteOffPolicyRequiredError",
    "ZeroEntryError",
    "ZeroLineError"
]


def _resolve_error_class(name: str) -> type[BaseException]:
    for module_name in _ERROR_MODULES:
        module = importlib.import_module(module_name)
        candidate = getattr(module, name, None)
        if isinstance(candidate, type) and issubclass(candidate, BaseException):
            return candidate
    raise RuntimeError(f"public error class not found: {name}")


def build_payload() -> dict[str, object]:
    error_codes: dict[str, str] = {}
    for class_name in _PUBLIC_ERROR_CLASS_NAMES:
        error_type = _resolve_error_class(class_name)
        code = getattr(error_type, "code", None)
        if not isinstance(code, str) or not code:
            raise RuntimeError(f"public error class {class_name} has no stable code")
        existing = error_codes.get(code)
        if existing is not None and existing != class_name:
            raise RuntimeError(f"duplicate public error code {code}: {existing}, {class_name}")
        error_codes[code] = class_name
    return {"version": project_version(), "error_codes": error_codes}


def main() -> int:
    check = parse_check_flag(__doc__ or "")
    return write_or_check(filename=_FILENAME, payload=build_payload(), check=check)


if __name__ == "__main__":
    raise SystemExit(main())
