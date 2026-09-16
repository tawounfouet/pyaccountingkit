"""Core enums for the LOT-18 subledger bounded context."""

from __future__ import annotations

from enum import StrEnum


class SubledgerType(StrEnum):
    ACCOUNTS_RECEIVABLE = "ACCOUNTS_RECEIVABLE"
    ACCOUNTS_PAYABLE = "ACCOUNTS_PAYABLE"
    OTHER = "OTHER"


class AuxiliaryMode(StrEnum):
    SUBLEDGER = "SUBLEDGER"
    EXTENDED_ACCOUNT_CODE = "EXTENDED_ACCOUNT_CODE"
    HYBRID = "HYBRID"


class SubledgerStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class SubledgerPartyType(StrEnum):
    CUSTOMER = "CUSTOMER"
    SUPPLIER = "SUPPLIER"
    BOTH = "BOTH"
    OTHER = "OTHER"


class SubledgerPartyStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class OperationalItemStatus(StrEnum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CANCELLED = "CANCELLED"


class AccountingEffectStatus(StrEnum):
    PENDING = "PENDING"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class BindingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AuxiliaryPolicyStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


__all__ = [
    "AccountingEffectStatus",
    "AuxiliaryMode",
    "AuxiliaryPolicyStatus",
    "BindingStatus",
    "OperationalItemStatus",
    "SubledgerPartyStatus",
    "SubledgerPartyType",
    "SubledgerStatus",
    "SubledgerType",
]
