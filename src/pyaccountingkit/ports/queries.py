"""Trial balance query port."""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.domain.reporting.trial_balance import (
    TrialBalance,
    TrialBalanceSnapshot,
)


class TrialBalanceProviderProtocol(Protocol):
    """Computes a verified trial balance for a given period and snapshot."""

    def balance_for(self, period_id: str, snapshot: TrialBalanceSnapshot) -> TrialBalance:
        """Return the trial balance; only POSTED entries contribute."""
        ...


__all__ = ["TrialBalanceProviderProtocol"]
