"""In-memory implementation of the persistent subledger repository."""

from __future__ import annotations

from pyaccountingkit.adapters.in_memory.repositories import ReadTracker
from pyaccountingkit.adapters.in_memory.store import InMemoryStore
from pyaccountingkit.adapters.subledger_codec import (
    MATCH,
    PARTY,
    PAYABLE,
    RECEIVABLE,
    REVERSAL,
    SETTLEMENT,
    SubledgerRecord,
    record_id,
    record_kind,
    require_record_type,
)
from pyaccountingkit.core.errors import RevisionConflictError
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.subledgers.allocation import SettlementAllocation
from pyaccountingkit.domain.subledgers.errors import (
    InvalidSettlementError,
    InvalidSubledgerConfigurationError,
    InvalidSubledgerItemError,
)
from pyaccountingkit.domain.subledgers.matching import AccountingMatch
from pyaccountingkit.domain.subledgers.parties import SubledgerParty
from pyaccountingkit.domain.subledgers.payable import Payable
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.settlement import Settlement
from pyaccountingkit.domain.subledgers.settlement_reversal import SettlementReversal


class InMemorySubledgerRepository:
    """Typed operational state in the UoW-local reference store."""

    def __init__(self, store: InMemoryStore, on_read: ReadTracker | None = None) -> None:
        self._store = store
        self._on_read = on_read

    @staticmethod
    def _key(kind: str, identifier: str) -> str:
        return f"{kind}:{identifier}"

    def _track(self, key: str) -> None:
        if self._on_read is not None:
            self._on_read("subledger_record", key)

    def _add(self, value: SubledgerRecord) -> None:
        kind = record_kind(value)
        identifier = record_id(value)
        key = self._key(kind, identifier)
        if key in self._store.subledger_records:
            raise RevisionConflictError(f"Subledger record {key} already exists")
        self._store.subledger_records[key] = value

    def _save(self, value: SubledgerRecord) -> None:
        kind = record_kind(value)
        identifier = record_id(value)
        key = self._key(kind, identifier)
        if key not in self._store.subledger_records:
            raise RevisionConflictError(f"Subledger record {key} does not exist")
        self._store.subledger_records[key] = value

    def _get(self, kind: str, identifier: str) -> SubledgerRecord:
        key = self._key(kind, identifier)
        self._track(key)
        try:
            return self._store.subledger_records[key]
        except KeyError as exc:
            if kind == PARTY:
                raise InvalidSubledgerConfigurationError(
                    f"subledger party {identifier!r} not found"
                ) from exc
            if kind == SETTLEMENT:
                raise InvalidSettlementError(f"settlement {identifier!r} not found") from exc
            raise InvalidSubledgerItemError(
                f"subledger record {kind}:{identifier!r} not found"
            ) from exc

    def add_party(self, party: SubledgerParty) -> None:
        self._add(party)

    def get_party(self, party_id: str, *, for_update: bool = False) -> SubledgerParty:
        value = self._get(PARTY, party_id)
        return require_record_type(value, SubledgerParty, identifier=party_id)

    def list_parties(self, entity_id: EntityId) -> tuple[SubledgerParty, ...]:
        values = tuple(
            value
            for value in self._store.subledger_records.values()
            if isinstance(value, SubledgerParty) and value.entity_id == entity_id
        )
        return tuple(sorted(values, key=lambda value: value.party_id))

    def add_receivable(self, item: Receivable) -> None:
        self._add(item)

    def save_receivable(self, item: Receivable) -> None:
        self._save(item)

    def get_receivable(self, item_id: str, *, for_update: bool = False) -> Receivable:
        value = self._get(RECEIVABLE, item_id)
        return require_record_type(value, Receivable, identifier=item_id)

    def list_open_receivables(
        self,
        entity_id: EntityId,
        subledger_id: str,
        *,
        party_id: str | None = None,
    ) -> tuple[Receivable, ...]:
        values = tuple(
            value
            for value in self._store.subledger_records.values()
            if isinstance(value, Receivable)
            and value.entity_id == entity_id
            and value.subledger_id == subledger_id
            and value.open_amount.amount > 0
            and (party_id is None or value.party_id == party_id)
        )
        return tuple(sorted(values, key=lambda value: value.receivable_id))

    def add_payable(self, item: Payable) -> None:
        self._add(item)

    def save_payable(self, item: Payable) -> None:
        self._save(item)

    def get_payable(self, item_id: str, *, for_update: bool = False) -> Payable:
        value = self._get(PAYABLE, item_id)
        return require_record_type(value, Payable, identifier=item_id)

    def list_open_payables(
        self,
        entity_id: EntityId,
        subledger_id: str,
        *,
        party_id: str | None = None,
    ) -> tuple[Payable, ...]:
        values = tuple(
            value
            for value in self._store.subledger_records.values()
            if isinstance(value, Payable)
            and value.entity_id == entity_id
            and value.subledger_id == subledger_id
            and value.open_amount.amount > 0
            and (party_id is None or value.party_id == party_id)
        )
        return tuple(sorted(values, key=lambda value: value.payable_id))

    def add_settlement(self, settlement: Settlement) -> None:
        self._add(settlement)

    def save_settlement(self, settlement: Settlement) -> None:
        self._save(settlement)

    def get_settlement(
        self,
        settlement_id: str,
        *,
        for_update: bool = False,
    ) -> Settlement:
        value = self._get(SETTLEMENT, settlement_id)
        return require_record_type(value, Settlement, identifier=settlement_id)

    def add_allocation(self, allocation: SettlementAllocation) -> None:
        self._add(allocation)

    def save_allocation(self, allocation: SettlementAllocation) -> None:
        self._save(allocation)

    def list_allocations(
        self,
        settlement_id: str,
        *,
        for_update: bool = False,
    ) -> tuple[SettlementAllocation, ...]:
        values = tuple(
            value
            for value in self._store.subledger_records.values()
            if isinstance(value, SettlementAllocation) and value.settlement_id == settlement_id
        )
        return tuple(sorted(values, key=lambda value: value.allocation_id))

    def append_reversal(self, reversal: SettlementReversal) -> None:
        self._add(reversal)

    def get_reversal(self, reversal_id: str) -> SettlementReversal | None:
        key = self._key(REVERSAL, reversal_id)
        self._track(key)
        value = self._store.subledger_records.get(key)
        if value is None:
            return None
        return require_record_type(
            value,
            SettlementReversal,
            identifier=reversal_id,
        )

    def add_match(self, match: AccountingMatch) -> None:
        self._add(match)

    def get_match(self, match_id: str) -> AccountingMatch | None:
        key = self._key(MATCH, match_id)
        self._track(key)
        value = self._store.subledger_records.get(key)
        if value is None:
            return None
        return require_record_type(value, AccountingMatch, identifier=match_id)


__all__ = ["InMemorySubledgerRepository"]
