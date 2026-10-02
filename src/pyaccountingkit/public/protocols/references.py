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
    ReferenceRelationProviderProtocol as _InternalReferenceRelationProviderProtocol,
)


class AccountingReferenceProviderProtocol(
    _InternalAccountingReferenceProviderProtocol,
    Protocol,
):
    """Stable extension surface implemented by structural reference providers."""


class ReferenceRelationProviderProtocol(
    _InternalReferenceRelationProviderProtocol,
    Protocol,
):
    """Extension surface for explicit regulatory standard relations."""


class EffectivePlanReferenceProviderProtocol(
    _InternalEffectivePlanReferenceProviderProtocol,
    Protocol,
):
    """Extension surface for provider-resolved effective account plans."""


__all__ = [
    "AccountingReferenceProviderProtocol",
    "EffectivePlanReferenceProviderProtocol",
    "ReferenceRelationProviderProtocol",
]
