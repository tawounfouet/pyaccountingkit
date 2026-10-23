"""Persistence port for the operational subledger chain."""

from __future__ import annotations

from typing import Protocol

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.subledgers.allocation import SettlementAllocation
from pyaccountingkit.domain.subledgers.matching import AccountingMatch
from pyaccountingkit.domain.subledgers.parties import SubledgerParty
from pyaccountingkit.domain.subledgers.payable import Payable
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.settlement import Settlement
from pyaccountingkit.domain.subledgers.settlement_reversal import SettlementReversal


class SubledgerRepositoryProtocol(Protocol):
    """Typed persistence boundary for subledger operational state."""

    def add_party(self, party: SubledgerParty) -> None: ...
    def get_party(self, party_id: str, *, for_update: bool = False) -> SubledgerParty: ...
    def list_parties(self, entity_id: EntityId) -> tuple[SubledgerParty, ...]: ...

    def add_receivable(self, item: Receivable) -> None: ...
    def save_receivable(self, item: Receivable) -> None: ...
    def get_receivable(self, item_id: str, *, for_update: bool = False) -> Receivable: ...
    def list_open_receivables(
        self,
        entity_id: EntityId,
        subledger_id: str,
        *,
        party_id: str | None = None,
    ) -> tuple[Receivable, ...]: ...

    def add_payable(self, item: Payable) -> None: ...
    def save_payable(self, item: Payable) -> None: ...
    def get_payable(self, item_id: str, *, for_update: bool = False) -> Payable: ...
    def list_open_payables(
        self,
        entity_id: EntityId,
        subledger_id: str,
        *,
        party_id: str | None = None,
    ) -> tuple[Payable, ...]: ...

    def add_settlement(self, settlement: Settlement) -> None: ...
    def save_settlement(self, settlement: Settlement) -> None: ...
    def get_settlement(
        self,
        settlement_id: str,
        *,
        for_update: bool = False,
    ) -> Settlement: ...

    def add_allocation(self, allocation: SettlementAllocation) -> None: ...
    def save_allocation(self, allocation: SettlementAllocation) -> None: ...
    def list_allocations(
        self,
        settlement_id: str,
        *,
        for_update: bool = False,
    ) -> tuple[SettlementAllocation, ...]: ...

    def append_reversal(self, reversal: SettlementReversal) -> None: ...
    def get_reversal(self, reversal_id: str) -> SettlementReversal | None: ...

    def add_match(self, match: AccountingMatch) -> None: ...
    def get_match(self, match_id: str) -> AccountingMatch | None: ...


__all__ = ["SubledgerRepositoryProtocol"]
