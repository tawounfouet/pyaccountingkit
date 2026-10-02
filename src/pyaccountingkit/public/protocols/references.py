"""Public accounting-reference extension contract."""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.ports.references import (
    AccountingReferenceProviderProtocol as _InternalAccountingReferenceProviderProtocol,
)
from pyaccountingkit.ports.references import (
    EffectivePlanReferenceProviderProtocol as _InternalEffectivePlanReferenceProviderProtocol,
)


class AccountingReferenceProviderProtocol(
    _InternalAccountingReferenceProviderProtocol,
    Protocol,
):
    """Stable extension surface implemented by structural reference providers."""


class EffectivePlanReferenceProviderProtocol(
    _InternalEffectivePlanReferenceProviderProtocol,
    Protocol,
):
    """Extension surface for provider-resolved effective account plans."""


__all__ = [
    "AccountingReferenceProviderProtocol",
    "EffectivePlanReferenceProviderProtocol",
]
