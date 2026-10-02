"""Public accounting-reference extension contract."""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.ports.references import (
    AccountingReferenceProviderProtocol as _InternalAccountingReferenceProviderProtocol,
)
from pyaccountingkit.ports.references import (
    EffectivePlanReferenceProviderProtocol as _InternalEffectivePlanReferenceProviderProtocol,
)
from pyaccountingkit.ports.references import (
    StandardRelationProviderProtocol as _InternalStandardRelationProviderProtocol,
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


class StandardRelationProviderProtocol(
    _InternalStandardRelationProviderProtocol,
    Protocol,
):
    """Extension surface for explicit standard relations and inference guards."""


__all__ = [
    "AccountingReferenceProviderProtocol",
    "EffectivePlanReferenceProviderProtocol",
    "StandardRelationProviderProtocol",
]
