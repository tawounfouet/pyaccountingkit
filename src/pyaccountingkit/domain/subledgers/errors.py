"""Stable subledger error taxonomy."""

from __future__ import annotations

from pyaccountingkit.core.errors import DomainError


class SubledgerError(DomainError):
    """Root of subledger errors."""

    code = "SUBLEDGER_ERROR"


class InvalidSubledgerConfigurationError(SubledgerError):
    code = "SUBLEDGER_INVALID_CONFIGURATION"


class InvalidSubledgerItemError(SubledgerError):
    code = "SUBLEDGER_INVALID_ITEM"


class InvalidDueItemError(InvalidSubledgerItemError):
    code = "SUBLEDGER_INVALID_DUE_ITEM"


class SubledgerAccountingLinkError(InvalidSubledgerItemError):
    code = "SUBLEDGER_ACCOUNTING_LINK_INVALID"


class ControlAccountNotConfiguredError(SubledgerError):
    code = "SUBLEDGER_CONTROL_ACCOUNT_NOT_CONFIGURED"


class AmbiguousControlAccountError(SubledgerError):
    code = "SUBLEDGER_CONTROL_ACCOUNT_AMBIGUOUS"


class AuxiliaryPolicyNotActiveError(SubledgerError):
    code = "SUBLEDGER_POLICY_NOT_ACTIVE"


class AuxiliaryPolicyNotEffectiveError(SubledgerError):
    code = "SUBLEDGER_POLICY_NOT_EFFECTIVE"


class InvalidSettlementError(SubledgerError):
    code = "SETTLEMENT_INVALID"


class SettlementNotAccountingEffectiveError(InvalidSettlementError):
    code = "SETTLEMENT_NOT_ACCOUNTING_EFFECTIVE"


class SettlementOverAllocationError(InvalidSettlementError):
    code = "SETTLEMENT_OVER_ALLOCATION"


class DueItemOverAllocationError(InvalidDueItemError):
    code = "DUE_ITEM_OVER_ALLOCATION"


class AllocationConcurrencyConflictError(SubledgerError):
    code = "ALLOCATION_CONCURRENCY_CONFLICT"


class SettlementAlreadyReversedError(InvalidSettlementError):
    code = "SETTLEMENT_ALREADY_REVERSED"


class InvalidMatchingError(SubledgerError):
    code = "MATCHING_INVALID"


class NonExecutableMatchingError(InvalidMatchingError):
    code = "MATCHING_NOT_EXECUTABLE"


class MatchOverAllocationError(InvalidMatchingError):
    code = "MATCHING_OVER_ALLOCATION"


class InvalidPaymentTermError(SubledgerError):
    code = "PAYMENT_TERM_INVALID"


class InvalidAgingPolicyError(SubledgerError):
    code = "AGING_POLICY_INVALID"


class InvalidAgingSourceError(SubledgerError):
    code = "AGING_SOURCE_INVALID"


class SubledgerReconciliationError(SubledgerError):
    code = "SUBLEDGER_RECONCILIATION_FAILED"


class WriteOffPolicyRequiredError(SubledgerError):
    code = "WRITE_OFF_POLICY_REQUIRED"


__all__ = [
    "AllocationConcurrencyConflictError",
    "AmbiguousControlAccountError",
    "AuxiliaryPolicyNotActiveError",
    "AuxiliaryPolicyNotEffectiveError",
    "ControlAccountNotConfiguredError",
    "DueItemOverAllocationError",
    "InvalidAgingPolicyError",
    "InvalidAgingSourceError",
    "InvalidDueItemError",
    "InvalidMatchingError",
    "InvalidPaymentTermError",
    "InvalidSettlementError",
    "InvalidSubledgerConfigurationError",
    "InvalidSubledgerItemError",
    "MatchOverAllocationError",
    "NonExecutableMatchingError",
    "SettlementAlreadyReversedError",
    "SettlementNotAccountingEffectiveError",
    "SettlementOverAllocationError",
    "SubledgerAccountingLinkError",
    "SubledgerError",
    "SubledgerReconciliationError",
    "WriteOffPolicyRequiredError",
]
