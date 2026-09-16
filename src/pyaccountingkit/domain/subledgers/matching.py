"""Explicit accounting matching, distinct from economic settlement allocation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.errors import (
    InvalidMatchingError,
    MatchOverAllocationError,
    NonExecutableMatchingError,
)


class MatchSide(StrEnum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class MatchStatus(StrEnum):
    VALIDATED = "VALIDATED"


@dataclass(frozen=True, slots=True)
class AccountingMatchItem:
    item_id: str
    entity_id: EntityId
    subledger_id: str
    party_id: str
    side: MatchSide
    amount: Money
    accounting_reference: PostedAccountingReference

    def __post_init__(self) -> None:
        for name in ("item_id", "subledger_id", "party_id"):
            if not getattr(self, name).strip():
                raise InvalidMatchingError(f"{name} must not be empty")
        if self.amount.amount <= 0:
            raise InvalidMatchingError("matching item amount must be strictly positive")
        require_same_entity(
            self.entity_id,
            self.accounting_reference.entity_id,
            resource=f"matching item {self.item_id} accounting reference",
        )


@dataclass(frozen=True, slots=True)
class MatchingCandidate:
    candidate_id: str
    entity_id: EntityId
    subledger_id: str
    party_id: str
    items: tuple[AccountingMatchItem, ...]

    def __post_init__(self) -> None:
        for name in ("candidate_id", "subledger_id", "party_id"):
            if not getattr(self, name).strip():
                raise InvalidMatchingError(f"{name} must not be empty")
        if len(self.items) < 2:
            raise InvalidMatchingError("matching candidate requires at least two items")
        currencies = {item.amount.currency for item in self.items}
        if len(currencies) != 1:
            raise InvalidMatchingError("matching candidate must use one currency")
        item_ids: set[str] = set()
        for item in self.items:
            require_same_entity(
                self.entity_id,
                item.entity_id,
                resource=f"matching item {item.item_id}",
            )
            if item.subledger_id != self.subledger_id:
                raise InvalidMatchingError("matching items must belong to the candidate subledger")
            if item.party_id != self.party_id:
                raise InvalidMatchingError("matching items must belong to the candidate party")
            if item.item_id in item_ids:
                raise InvalidMatchingError("matching candidate item ids must be unique")
            item_ids.add(item.item_id)
        sides = {item.side for item in self.items}
        if sides != {MatchSide.DEBIT, MatchSide.CREDIT}:
            raise InvalidMatchingError("matching candidate requires both debit and credit items")

    @property
    def currency(self) -> Currency:
        return self.items[0].amount.currency

    @property
    def debit_total(self) -> Money:
        total = Money.zero(self.currency)
        for item in self.items:
            if item.side is MatchSide.DEBIT:
                total += item.amount
        return total

    @property
    def credit_total(self) -> Money:
        total = Money.zero(self.currency)
        for item in self.items:
            if item.side is MatchSide.CREDIT:
                total += item.amount
        return total

    def assert_executable(self) -> None:
        raise NonExecutableMatchingError(
            f"matching candidate {self.candidate_id!r} must be explicitly validated first"
        )

    def checksum(self) -> str:
        payload = {
            "candidate_id": self.candidate_id,
            "entity_id": str(self.entity_id),
            "subledger_id": self.subledger_id,
            "party_id": self.party_id,
            "items": [
                {
                    "item_id": item.item_id,
                    "side": item.side.value,
                    "amount": str(item.amount.amount),
                    "currency": str(item.amount.currency.code),
                    "entry_id": str(item.accounting_reference.entry_id),
                }
                for item in sorted(self.items, key=lambda value: value.item_id)
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def validate(
        self,
        *,
        match_id: str,
        validated_at: datetime,
        residual_amount: Money | None = None,
    ) -> AccountingMatch:
        if not match_id.strip():
            raise InvalidMatchingError("match_id must not be empty")
        difference = self.debit_total - self.credit_total
        absolute_difference = abs(difference)
        if absolute_difference.is_zero():
            if residual_amount is not None and not residual_amount.is_zero():
                raise MatchOverAllocationError(
                    "balanced matching candidate cannot declare a non-zero residual"
                )
            normalized_residual = Money.zero(self.currency)
            residual_side = None
        else:
            if residual_amount is None:
                raise NonExecutableMatchingError(
                    "partial matching requires an explicit residual amount"
                )
            if residual_amount.currency != self.currency:
                raise InvalidMatchingError("matching residual currency must match candidate")
            if residual_amount.amount <= 0 or residual_amount != absolute_difference:
                raise MatchOverAllocationError(
                    "matching residual must equal the unmatched debit/credit difference exactly"
                )
            normalized_residual = residual_amount
            residual_side = MatchSide.DEBIT if difference.amount > 0 else MatchSide.CREDIT

        matched_amount = (
            self.credit_total
            if self.debit_total.compare(self.credit_total) >= 0
            else self.debit_total
        )
        if matched_amount.is_zero():
            raise NonExecutableMatchingError("validated matching amount must be strictly positive")
        return AccountingMatch(
            match_id=match_id,
            candidate_id=self.candidate_id,
            candidate_checksum=self.checksum(),
            entity_id=self.entity_id,
            subledger_id=self.subledger_id,
            party_id=self.party_id,
            items=self.items,
            matched_amount=matched_amount,
            residual_amount=normalized_residual,
            residual_side=residual_side,
            validated_at=validated_at,
        )


@dataclass(frozen=True, slots=True)
class AccountingMatch:
    match_id: str
    candidate_id: str
    candidate_checksum: str
    entity_id: EntityId
    subledger_id: str
    party_id: str
    items: tuple[AccountingMatchItem, ...]
    matched_amount: Money
    residual_amount: Money
    residual_side: MatchSide | None
    validated_at: datetime
    status: MatchStatus = MatchStatus.VALIDATED

    def __post_init__(self) -> None:
        for name in (
            "match_id",
            "candidate_id",
            "candidate_checksum",
            "subledger_id",
            "party_id",
        ):
            if not getattr(self, name).strip():
                raise InvalidMatchingError(f"{name} must not be empty")
        if self.matched_amount.amount <= 0:
            raise InvalidMatchingError("validated matching amount must be strictly positive")
        if self.residual_amount.currency != self.matched_amount.currency:
            raise InvalidMatchingError("matching residual currency must match matched amount")
        if self.residual_amount.amount < 0:
            raise InvalidMatchingError("matching residual cannot be negative")
        if self.residual_amount.is_zero() and self.residual_side is not None:
            raise InvalidMatchingError("full matching cannot declare a residual side")
        if not self.residual_amount.is_zero() and self.residual_side is None:
            raise InvalidMatchingError("partial matching requires a residual side")
        for item in self.items:
            require_same_entity(
                self.entity_id,
                item.entity_id,
                resource=f"matching item {item.item_id}",
            )

    def assert_executable(self) -> None:
        if self.status is not MatchStatus.VALIDATED:
            raise NonExecutableMatchingError(f"matching {self.match_id!r} is not validated")


__all__ = [
    "AccountingMatch",
    "AccountingMatchItem",
    "MatchSide",
    "MatchStatus",
    "MatchingCandidate",
]
