"""Append-only persistence port for accounting execution traces."""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.core.identifiers import EntryId
from pyaccountingkit.domain.traceability.accounting_execution import AccountingExecutionTrace


class AccountingExecutionTraceRepositoryProtocol(Protocol):
    """Durably bind one proposal execution trace to its journal entry."""

    def append(self, trace: AccountingExecutionTrace) -> None:
        """Persist a new immutable trace in the active transaction."""
        ...

    def get_by_entry_id(self, entry_id: EntryId) -> AccountingExecutionTrace | None:
        """Return the durable trace for one journal entry, when present."""
        ...


__all__ = ["AccountingExecutionTraceRepositoryProtocol"]
