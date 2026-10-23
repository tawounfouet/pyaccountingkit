"""Django/PostgreSQL implementation of the typed subledger repository."""

from __future__ import annotations

from django.db import IntegrityError

from pyaccountingkit.adapters.django.models import SubledgerRecordModel
from pyaccountingkit.adapters.subledger_codec import (
    ALLOCATION,
    MATCH,
    PARTY,
    PAYABLE,
    RECEIVABLE,
    REVERSAL,
    SETTLEMENT,
    SubledgerRecord,
    decode_record,
    encode_record,
    entity_id,
    record_id,
    record_kind,
    require_record_type,
    subledger_id,
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


class DjangoSubledgerRepository:
    """Persist typed subledger records in the active Django transaction."""

    def __init__(self, *, using: str = "default") -> None:
        self._using = using

    @staticmethod
    def _key(kind: str, identifier: str) -> str:
        return f"{kind}:{identifier}"

    def _add(self, value: SubledgerRecord) -> None:
        kind = record_kind(value)
        identifier = record_id(value)
        try:
            SubledgerRecordModel.objects.using(self._using).create(
                key=self._key(kind, identifier),
                kind=kind,
                record_id=identifier,
                entity_id=str(entity_id(value)),
                subledger_id=subledger_id(value),
                revision=0,
                payload=encode_record(value),
            )
        except IntegrityError as exc:
            raise RevisionConflictError(
                f"Subledger record {kind}:{identifier} already exists"
            ) from exc

    def _save(self, value: SubledgerRecord) -> None:
        kind = record_kind(value)
        identifier = record_id(value)
        row = (
            SubledgerRecordModel.objects.using(self._using)
            .select_for_update()
            .filter(key=self._key(kind, identifier))
            .first()
        )
        if row is None:
            raise RevisionConflictError(f"Subledger record {kind}:{identifier} does not exist")
        row.entity_id = str(entity_id(value))
        row.subledger_id = subledger_id(value)
        row.payload = encode_record(value)
        row.revision += 1
        row.save(
            using=self._using,
            update_fields=("entity_id", "subledger_id", "payload", "revision"),
        )

    def _get(
        self,
        kind: str,
        identifier: str,
        *,
        for_update: bool = False,
    ) -> SubledgerRecord:
        query = SubledgerRecordModel.objects.using(self._using)
        if for_update:
            query = query.select_for_update()
        row = query.filter(key=self._key(kind, identifier)).first()
        if row is None:
            if kind == PARTY:
                raise InvalidSubledgerConfigurationError(
                    f"subledger party {identifier!r} not found"
                )
            if kind == SETTLEMENT:
                raise InvalidSettlementError(f"settlement {identifier!r} not found")
            raise InvalidSubledgerItemError(
                f"subledger record {kind}:{identifier!r} not found"
            )
        return decode_record(row.kind, dict(row.payload))

    def _list_scope(
        self,
        *,
        kind: str,
        entity: EntityId,
        subledger: str | None = None,
    ) -> tuple[SubledgerRecord, ...]:
        query = SubledgerRecordModel.objects.using(self._using).filter(
            kind=kind,
            entity_id=str(entity),
        )
        if subledger is not None:
            query = query.filter(subledger_id=subledger)
        rows = query.order_by("record_id")
        return tuple(decode_record(row.kind, dict(row.payload)) for row in rows)

    def add_party(self, party: SubledgerParty) -> None:
        self._add(party)

    def get_party(self, party_id: str, *, for_update: bool = False) -> SubledgerParty:
        value = self._get(PARTY, party_id, for_update=for_update)
        return require_record_type(value, SubledgerParty, identifier=party_id)

    def list_parties(self, entity_id: EntityId) -> tuple[SubledgerParty, ...]:
        values = self._list_scope(kind=PARTY, entity=entity_id)
        return tuple(value for value in values if isinstance(value, SubledgerParty))

    def add_receivable(self, item: Receivable) -> None:
        self._add(item)

    def save_receivable(self, item: Receivable) -> None:
        self._save(item)

    def get_receivable(self, item_id: str, *, for_update: bool = False) -> Receivable:
        value = self._get(RECEIVABLE, item_id, for_update=for_update)
        return require_record_type(value, Receivable, identifier=item_id)

    def list_open_receivables(
        self,
        entity_id: EntityId,
        subledger_id: str,
        *,
        party_id: str | None = None,
    ) -> tuple[Receivable, ...]:
        values = self._list_scope(kind=RECEIVABLE, entity=entity_id, subledger=subledger_id)
        return tuple(
            value
            for value in values
            if isinstance(value, Receivable)
            and value.open_amount.amount > 0
            and (party_id is None or value.party_id == party_id)
        )

    def add_payable(self, item: Payable) -> None:
        self._add(item)

    def save_payable(self, item: Payable) -> None:
        self._save(item)

    def get_payable(self, item_id: str, *, for_update: bool = False) -> Payable:
        value = self._get(PAYABLE, item_id, for_update=for_update)
        return require_record_type(value, Payable, identifier=item_id)

    def list_open_payables(
        self,
        entity_id: EntityId,
        subledger_id: str,
        *,
        party_id: str | None = None,
    ) -> tuple[Payable, ...]:
        values = self._list_scope(kind=PAYABLE, entity=entity_id, subledger=subledger_id)
        return tuple(
            value
            for value in values
            if isinstance(value, Payable)
            and value.open_amount.amount > 0
            and (party_id is None or value.party_id == party_id)
        )

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
        value = self._get(SETTLEMENT, settlement_id, for_update=for_update)
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
        query = SubledgerRecordModel.objects.using(self._using).filter(kind=ALLOCATION)
        if for_update:
            query = query.select_for_update()
        values = tuple(
            decode_record(row.kind, dict(row.payload))
            for row in query.order_by("record_id")
        )
        return tuple(
            value
            for value in values
            if isinstance(value, SettlementAllocation)
            and value.settlement_id == settlement_id
        )

    def append_reversal(self, reversal: SettlementReversal) -> None:
        self._add(reversal)

    def get_reversal(self, reversal_id: str) -> SettlementReversal | None:
        row = (
            SubledgerRecordModel.objects.using(self._using)
            .filter(key=self._key(REVERSAL, reversal_id))
            .first()
        )
        if row is None:
            return None
        value = decode_record(row.kind, dict(row.payload))
        return require_record_type(
            value,
            SettlementReversal,
            identifier=reversal_id,
        )

    def add_match(self, match: AccountingMatch) -> None:
        self._add(match)

    def get_match(self, match_id: str) -> AccountingMatch | None:
        row = (
            SubledgerRecordModel.objects.using(self._using)
            .filter(key=self._key(MATCH, match_id))
            .first()
        )
        if row is None:
            return None
        value = decode_record(row.kind, dict(row.payload))
        return require_record_type(value, AccountingMatch, identifier=match_id)


__all__ = ["DjangoSubledgerRepository"]
