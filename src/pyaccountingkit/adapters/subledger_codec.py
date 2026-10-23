"""Adapter-neutral JSON codec for persistent subledger aggregates."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pyaccountingkit.core.currency import Currency, CurrencyCode
from pyaccountingkit.core.identifiers import EntityId, EntryId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.allocation import AllocationStatus, SettlementAllocation
from pyaccountingkit.domain.subledgers.auxiliary import AuxiliaryReference
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.matching import (
    AccountingMatch,
    AccountingMatchItem,
    MatchSide,
    MatchStatus,
)
from pyaccountingkit.domain.subledgers.parties import PartyRef, SubledgerParty
from pyaccountingkit.domain.subledgers.payable import Payable
from pyaccountingkit.domain.subledgers.primitives import (
    AccountingEffectStatus,
    OperationalItemStatus,
    SubledgerPartyStatus,
    SubledgerPartyType,
)
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.settlement import Settlement, SettlementStatus
from pyaccountingkit.domain.subledgers.settlement_reversal import SettlementReversal

SubledgerRecord = (
    SubledgerParty
    | Receivable
    | Payable
    | Settlement
    | SettlementAllocation
    | SettlementReversal
    | AccountingMatch
)

PARTY = "PARTY"
RECEIVABLE = "RECEIVABLE"
PAYABLE = "PAYABLE"
SETTLEMENT = "SETTLEMENT"
ALLOCATION = "ALLOCATION"
REVERSAL = "REVERSAL"
MATCH = "MATCH"


def record_kind(value: SubledgerRecord) -> str:
    if isinstance(value, SubledgerParty):
        return PARTY
    if isinstance(value, Receivable):
        return RECEIVABLE
    if isinstance(value, Payable):
        return PAYABLE
    if isinstance(value, Settlement):
        return SETTLEMENT
    if isinstance(value, SettlementAllocation):
        return ALLOCATION
    if isinstance(value, SettlementReversal):
        return REVERSAL
    if isinstance(value, AccountingMatch):
        return MATCH
    raise TypeError(f"unsupported subledger record type: {type(value)!r}")


def record_id(value: SubledgerRecord) -> str:
    if isinstance(value, SubledgerParty):
        return value.party_id
    if isinstance(value, Receivable):
        return value.receivable_id
    if isinstance(value, Payable):
        return value.payable_id
    if isinstance(value, Settlement):
        return value.settlement_id
    if isinstance(value, SettlementAllocation):
        return value.allocation_id
    if isinstance(value, SettlementReversal):
        return value.reversal_id
    if isinstance(value, AccountingMatch):
        return value.match_id
    raise TypeError(f"unsupported subledger record type: {type(value)!r}")


def entity_id(value: SubledgerRecord) -> EntityId:
    return value.entity_id


def subledger_id(value: SubledgerRecord) -> str:
    if isinstance(value, SubledgerParty):
        return ""
    return value.subledger_id if hasattr(value, "subledger_id") else ""


def encode_record(value: SubledgerRecord) -> dict[str, Any]:
    if isinstance(value, SubledgerParty):
        return _encode_party(value)
    if isinstance(value, Receivable):
        return _encode_receivable(value)
    if isinstance(value, Payable):
        return _encode_payable(value)
    if isinstance(value, Settlement):
        return _encode_settlement(value)
    if isinstance(value, SettlementAllocation):
        return _encode_allocation(value)
    if isinstance(value, SettlementReversal):
        return _encode_reversal(value)
    if isinstance(value, AccountingMatch):
        return _encode_match(value)
    raise TypeError(f"unsupported subledger record type: {type(value)!r}")


def decode_record(kind: str, payload: dict[str, Any]) -> SubledgerRecord:
    if kind == PARTY:
        return _decode_party(payload)
    if kind == RECEIVABLE:
        return _decode_receivable(payload)
    if kind == PAYABLE:
        return _decode_payable(payload)
    if kind == SETTLEMENT:
        return _decode_settlement(payload)
    if kind == ALLOCATION:
        return _decode_allocation(payload)
    if kind == REVERSAL:
        return _decode_reversal(payload)
    if kind == MATCH:
        return _decode_match(payload)
    raise ValueError(f"unknown subledger record kind: {kind!r}")


def _money(value: Money) -> dict[str, Any]:
    return {
        "amount": str(value.amount),
        "currency": str(value.currency.code),
        "exponent": value.currency.exponent,
    }


def _decode_money(payload: dict[str, Any]) -> Money:
    currency = Currency(
        CurrencyCode(str(payload["currency"])),
        exponent=int(payload["exponent"]),
    )
    return Money(Decimal(str(payload["amount"])), currency)


def _reference(value: PostedAccountingReference | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "entity_id": str(value.entity_id),
        "entry_id": str(value.entry_id),
        "posted_at": value.posted_at.isoformat(),
    }


def _decode_reference(payload: dict[str, Any] | None) -> PostedAccountingReference | None:
    if payload is None:
        return None
    return PostedAccountingReference(
        entity_id=EntityId(str(payload["entity_id"])),
        entry_id=EntryId(str(payload["entry_id"])),
        posted_at=datetime.fromisoformat(str(payload["posted_at"])),
    )


def _due_item(value: DueItem) -> dict[str, Any]:
    return {
        "due_item_id": value.due_item_id,
        "entity_id": str(value.entity_id),
        "source_subledger_item_id": value.source_subledger_item_id,
        "due_date": value.due_date.isoformat(),
        "original_amount": _money(value.original_amount),
        "open_amount": _money(value.open_amount),
        "revision": value.revision,
    }


def _decode_due_item(payload: dict[str, Any]) -> DueItem:
    return DueItem(
        due_item_id=str(payload["due_item_id"]),
        entity_id=EntityId(str(payload["entity_id"])),
        source_subledger_item_id=str(payload["source_subledger_item_id"]),
        due_date=date.fromisoformat(str(payload["due_date"])),
        original_amount=_decode_money(payload["original_amount"]),
        open_amount=_decode_money(payload["open_amount"]),
        revision=int(payload["revision"]),
    )


def _encode_party(value: SubledgerParty) -> dict[str, Any]:
    return {
        "party_id": value.party_id,
        "entity_id": str(value.entity_id),
        "party_type": value.party_type.value,
        "display_name": value.display_name,
        "external_ref": (
            {"system": value.external_ref.system, "value": value.external_ref.value}
            if value.external_ref is not None
            else None
        ),
        "auxiliary_reference": (
            {
                "system": value.auxiliary_reference.system,
                "code": value.auxiliary_reference.code,
                "label": value.auxiliary_reference.label,
            }
            if value.auxiliary_reference is not None
            else None
        ),
        "status": value.status.value,
    }


def _decode_party(payload: dict[str, Any]) -> SubledgerParty:
    external = payload.get("external_ref")
    auxiliary = payload.get("auxiliary_reference")
    return SubledgerParty(
        party_id=str(payload["party_id"]),
        entity_id=EntityId(str(payload["entity_id"])),
        party_type=SubledgerPartyType(str(payload["party_type"])),
        display_name=str(payload["display_name"]),
        external_ref=(
            PartyRef(system=str(external["system"]), value=str(external["value"]))
            if isinstance(external, dict)
            else None
        ),
        auxiliary_reference=(
            AuxiliaryReference(
                system=str(auxiliary["system"]),
                code=str(auxiliary["code"]),
                label=(str(auxiliary["label"]) if auxiliary.get("label") is not None else None),
            )
            if isinstance(auxiliary, dict)
            else None
        ),
        status=SubledgerPartyStatus(str(payload["status"])),
    )


def _encode_receivable(value: Receivable) -> dict[str, Any]:
    return {
        "receivable_id": value.receivable_id,
        "entity_id": str(value.entity_id),
        "subledger_id": value.subledger_id,
        "party_id": value.party_id,
        "source_document_ref": value.source_document_ref,
        "original_amount": _money(value.original_amount),
        "accounting_date": value.accounting_date.isoformat(),
        "due_items": [_due_item(item) for item in value.due_items],
        "operational_status": value.operational_status.value,
        "accounting_status": value.accounting_status.value,
        "accounting_reference": _reference(value.accounting_reference),
    }


def _decode_receivable(payload: dict[str, Any]) -> Receivable:
    return Receivable(
        receivable_id=str(payload["receivable_id"]),
        entity_id=EntityId(str(payload["entity_id"])),
        subledger_id=str(payload["subledger_id"]),
        party_id=str(payload["party_id"]),
        source_document_ref=str(payload["source_document_ref"]),
        original_amount=_decode_money(payload["original_amount"]),
        accounting_date=date.fromisoformat(str(payload["accounting_date"])),
        due_items=tuple(_decode_due_item(item) for item in payload["due_items"]),
        operational_status=OperationalItemStatus(str(payload["operational_status"])),
        accounting_status=AccountingEffectStatus(str(payload["accounting_status"])),
        accounting_reference=_decode_reference(payload.get("accounting_reference")),
    )


def _encode_payable(value: Payable) -> dict[str, Any]:
    return {
        "payable_id": value.payable_id,
        "entity_id": str(value.entity_id),
        "subledger_id": value.subledger_id,
        "party_id": value.party_id,
        "source_document_ref": value.source_document_ref,
        "original_amount": _money(value.original_amount),
        "accounting_date": value.accounting_date.isoformat(),
        "due_items": [_due_item(item) for item in value.due_items],
        "operational_status": value.operational_status.value,
        "accounting_status": value.accounting_status.value,
        "accounting_reference": _reference(value.accounting_reference),
    }


def _decode_payable(payload: dict[str, Any]) -> Payable:
    return Payable(
        payable_id=str(payload["payable_id"]),
        entity_id=EntityId(str(payload["entity_id"])),
        subledger_id=str(payload["subledger_id"]),
        party_id=str(payload["party_id"]),
        source_document_ref=str(payload["source_document_ref"]),
        original_amount=_decode_money(payload["original_amount"]),
        accounting_date=date.fromisoformat(str(payload["accounting_date"])),
        due_items=tuple(_decode_due_item(item) for item in payload["due_items"]),
        operational_status=OperationalItemStatus(str(payload["operational_status"])),
        accounting_status=AccountingEffectStatus(str(payload["accounting_status"])),
        accounting_reference=_decode_reference(payload.get("accounting_reference")),
    )


def _encode_settlement(value: Settlement) -> dict[str, Any]:
    return {
        "settlement_id": value.settlement_id,
        "entity_id": str(value.entity_id),
        "subledger_id": value.subledger_id,
        "settlement_date": value.settlement_date.isoformat(),
        "accounting_date": value.accounting_date.isoformat(),
        "amount": _money(value.amount),
        "open_amount": _money(value.open_amount),
        "source_reference": value.source_reference,
        "party_id": value.party_id,
        "status": value.status.value,
        "accounting_status": value.accounting_status.value,
        "accounting_reference": _reference(value.accounting_reference),
        "reversal_accounting_reference": _reference(value.reversal_accounting_reference),
        "revision": value.revision,
        "reversed_by_id": value.reversed_by_id,
    }


def _decode_settlement(payload: dict[str, Any]) -> Settlement:
    return Settlement(
        settlement_id=str(payload["settlement_id"]),
        entity_id=EntityId(str(payload["entity_id"])),
        subledger_id=str(payload["subledger_id"]),
        settlement_date=date.fromisoformat(str(payload["settlement_date"])),
        accounting_date=date.fromisoformat(str(payload["accounting_date"])),
        amount=_decode_money(payload["amount"]),
        open_amount=_decode_money(payload["open_amount"]),
        source_reference=str(payload["source_reference"]),
        party_id=(str(payload["party_id"]) if payload.get("party_id") is not None else None),
        status=SettlementStatus(str(payload["status"])),
        accounting_status=AccountingEffectStatus(str(payload["accounting_status"])),
        accounting_reference=_decode_reference(payload.get("accounting_reference")),
        reversal_accounting_reference=_decode_reference(
            payload.get("reversal_accounting_reference")
        ),
        revision=int(payload["revision"]),
        reversed_by_id=(
            str(payload["reversed_by_id"]) if payload.get("reversed_by_id") is not None else None
        ),
    )


def _encode_allocation(value: SettlementAllocation) -> dict[str, Any]:
    return {
        "allocation_id": value.allocation_id,
        "entity_id": str(value.entity_id),
        "settlement_id": value.settlement_id,
        "due_item_id": value.due_item_id,
        "source_item_id": value.source_item_id,
        "amount": _money(value.amount),
        "allocation_date": value.allocation_date.isoformat(),
        "settlement_revision": value.settlement_revision,
        "due_item_revision": value.due_item_revision,
        "status": value.status.value,
        "reversed_at": value.reversed_at.isoformat() if value.reversed_at else None,
    }


def _decode_allocation(payload: dict[str, Any]) -> SettlementAllocation:
    return SettlementAllocation(
        allocation_id=str(payload["allocation_id"]),
        entity_id=EntityId(str(payload["entity_id"])),
        settlement_id=str(payload["settlement_id"]),
        due_item_id=str(payload["due_item_id"]),
        source_item_id=str(payload["source_item_id"]),
        amount=_decode_money(payload["amount"]),
        allocation_date=date.fromisoformat(str(payload["allocation_date"])),
        settlement_revision=int(payload["settlement_revision"]),
        due_item_revision=int(payload["due_item_revision"]),
        status=AllocationStatus(str(payload["status"])),
        reversed_at=(
            datetime.fromisoformat(str(payload["reversed_at"]))
            if payload.get("reversed_at") is not None
            else None
        ),
    )


def _encode_reversal(value: SettlementReversal) -> dict[str, Any]:
    return {
        "reversal_id": value.reversal_id,
        "entity_id": str(value.entity_id),
        "settlement_id": value.settlement_id,
        "reversed_at": value.reversed_at.isoformat(),
        "reversed_allocation_ids": list(value.reversed_allocation_ids),
        "accounting_reversal_reference": _reference(value.accounting_reversal_reference),
        "reason": value.reason,
    }


def _decode_reversal(payload: dict[str, Any]) -> SettlementReversal:
    reference = _decode_reference(payload["accounting_reversal_reference"])
    if reference is None:
        raise ValueError("settlement reversal payload requires accounting reference")
    return SettlementReversal(
        reversal_id=str(payload["reversal_id"]),
        entity_id=EntityId(str(payload["entity_id"])),
        settlement_id=str(payload["settlement_id"]),
        reversed_at=datetime.fromisoformat(str(payload["reversed_at"])),
        reversed_allocation_ids=tuple(str(item) for item in payload["reversed_allocation_ids"]),
        accounting_reversal_reference=reference,
        reason=str(payload["reason"]),
    )


def _match_item(value: AccountingMatchItem) -> dict[str, Any]:
    return {
        "item_id": value.item_id,
        "entity_id": str(value.entity_id),
        "subledger_id": value.subledger_id,
        "party_id": value.party_id,
        "side": value.side.value,
        "amount": _money(value.amount),
        "accounting_reference": _reference(value.accounting_reference),
    }


def _decode_match_item(payload: dict[str, Any]) -> AccountingMatchItem:
    reference = _decode_reference(payload["accounting_reference"])
    if reference is None:
        raise ValueError("matching item payload requires accounting reference")
    return AccountingMatchItem(
        item_id=str(payload["item_id"]),
        entity_id=EntityId(str(payload["entity_id"])),
        subledger_id=str(payload["subledger_id"]),
        party_id=str(payload["party_id"]),
        side=MatchSide(str(payload["side"])),
        amount=_decode_money(payload["amount"]),
        accounting_reference=reference,
    )


def _encode_match(value: AccountingMatch) -> dict[str, Any]:
    return {
        "match_id": value.match_id,
        "candidate_id": value.candidate_id,
        "candidate_checksum": value.candidate_checksum,
        "entity_id": str(value.entity_id),
        "subledger_id": value.subledger_id,
        "party_id": value.party_id,
        "items": [_match_item(item) for item in value.items],
        "matched_amount": _money(value.matched_amount),
        "residual_amount": _money(value.residual_amount),
        "residual_side": value.residual_side.value if value.residual_side else None,
        "validated_at": value.validated_at.isoformat(),
        "status": value.status.value,
    }


def _decode_match(payload: dict[str, Any]) -> AccountingMatch:
    residual_side = payload.get("residual_side")
    return AccountingMatch(
        match_id=str(payload["match_id"]),
        candidate_id=str(payload["candidate_id"]),
        candidate_checksum=str(payload["candidate_checksum"]),
        entity_id=EntityId(str(payload["entity_id"])),
        subledger_id=str(payload["subledger_id"]),
        party_id=str(payload["party_id"]),
        items=tuple(_decode_match_item(item) for item in payload["items"]),
        matched_amount=_decode_money(payload["matched_amount"]),
        residual_amount=_decode_money(payload["residual_amount"]),
        residual_side=MatchSide(str(residual_side)) if residual_side is not None else None,
        validated_at=datetime.fromisoformat(str(payload["validated_at"])),
        status=MatchStatus(str(payload["status"])),
    )


__all__ = [
    "ALLOCATION",
    "MATCH",
    "PARTY",
    "PAYABLE",
    "RECEIVABLE",
    "REVERSAL",
    "SETTLEMENT",
    "SubledgerRecord",
    "decode_record",
    "encode_record",
    "entity_id",
    "record_id",
    "record_kind",
    "subledger_id",
]
