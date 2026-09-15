"""Account code and role values for the company chart of accounts."""

from __future__ import annotations

from enum import StrEnum


class AccountRole(StrEnum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"
    OTHER = "OTHER"


__all__ = ["AccountRole"]
