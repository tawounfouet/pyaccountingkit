"""Accounting entity root of the identity bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.identifiers import EntityId


@dataclass(frozen=True, slots=True)
class AccountingEntity:
    """A legal accounting unit that owns charts, journals and ledgers."""

    id: EntityId
    name: str
    default_currency: Currency
    active: bool = True


__all__ = ["AccountingEntity"]
