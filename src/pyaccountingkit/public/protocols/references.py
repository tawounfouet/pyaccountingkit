"""Public accounting-reference extension contract."""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.ports.references import (
    AccountingReferenceProviderProtocol as _InternalAccountingReferenceProviderProtocol,
)


class AccountingReferenceProviderProtocol(
    _InternalAccountingReferenceProviderProtocol,
    Protocol,
):
    """Stable extension surface implemented by accounting-reference providers."""


__all__ = ["AccountingReferenceProviderProtocol"]
