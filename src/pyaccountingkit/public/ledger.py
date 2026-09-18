"""Public ledger query facade."""

from __future__ import annotations

from pyaccountingkit.public._base import PublicNamespace
from pyaccountingkit.public.context import CommandContext


class LedgerAPI(PublicNamespace):
    """Framework-neutral ledger namespace."""

    def __init__(self, service: object | None = None) -> None:
        super().__init__("ledger", service)

    def journal(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `ledger.journal` public operation."""
        return self._invoke("journal", context=context, **parameters)

    def general_ledger(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `ledger.general_ledger` public operation."""
        return self._invoke("general_ledger", context=context, **parameters)

    def trial_balance(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `ledger.trial_balance` public operation."""
        return self._invoke("trial_balance", context=context, **parameters)

    def account_balance(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `ledger.account_balance` public operation."""
        return self._invoke("account_balance", context=context, **parameters)

    def entry_history(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `ledger.entry_history` public operation."""
        return self._invoke("entry_history", context=context, **parameters)

    def snapshot_trial_balance(
        self,
        *,
        context: CommandContext | None = None,
        **parameters: object,
    ) -> object:
        """Execute the explicit `ledger.snapshot_trial_balance` public operation."""
        return self._invoke("snapshot_trial_balance", context=context, **parameters)


__all__ = ["LedgerAPI"]
