"""Stable LOT-18 subledger error taxonomy."""

from __future__ import annotations

from pyaccountingkit.core.errors import DomainError


class SubledgerError(DomainError):
    """Root of subledger-foundation errors."""

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


__all__ = [
    "AmbiguousControlAccountError",
    "AuxiliaryPolicyNotActiveError",
    "AuxiliaryPolicyNotEffectiveError",
    "ControlAccountNotConfiguredError",
    "InvalidDueItemError",
    "InvalidSubledgerConfigurationError",
    "InvalidSubledgerItemError",
    "SubledgerAccountingLinkError",
    "SubledgerError",
]
