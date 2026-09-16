"""Deterministic subledger aging without impairment semantics."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.errors import InvalidAgingPolicyError, InvalidAgingSourceError
from pyaccountingkit.domain.subledgers.payable import Payable
from pyaccountingkit.domain.subledgers.receivable import Receivable


class AgingDateBasis(StrEnum):
    DUE_DATE = "DUE_DATE"
    ACCOUNTING_DATE = "ACCOUNTING_DATE"


@dataclass(frozen=True, slots=True)
class AgingBucketDefinition:
    bucket_id: str
    min_days: int | None
    max_days: int | None

    def __post_init__(self) -> None:
        if not self.bucket_id.strip():
            raise InvalidAgingPolicyError("aging bucket_id must not be empty")
        if self.min_days is not None and self.max_days is not None:
            if self.min_days > self.max_days:
                raise InvalidAgingPolicyError("aging bucket min_days cannot exceed max_days")

    def contains(self, days: int) -> bool:
        return (self.min_days is None or days >= self.min_days) and (
            self.max_days is None or days <= self.max_days
        )


@dataclass(frozen=True, slots=True)
class AgingPolicy:
    policy_id: str
    version: str
    date_basis: AgingDateBasis
    buckets: tuple[AgingBucketDefinition, ...]

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise InvalidAgingPolicyError("aging policy_id must not be empty")
        if not self.version.strip():
            raise InvalidAgingPolicyError("aging policy version must not be empty")
        if not self.buckets:
            raise InvalidAgingPolicyError("aging policy requires at least one bucket")
        ids = tuple(bucket.bucket_id for bucket in self.buckets)
        if len(set(ids)) != len(ids):
            raise InvalidAgingPolicyError("aging bucket ids must be unique")
        self._validate_partition()

    @property
    def ordered_buckets(self) -> tuple[AgingBucketDefinition, ...]:
        return tuple(
            sorted(
                self.buckets,
                key=lambda bucket: (
                    bucket.min_days is not None,
                    bucket.min_days if bucket.min_days is not None else 0,
                    bucket.bucket_id,
                ),
            )
        )

    def _validate_partition(self) -> None:
        ordered = self.ordered_buckets
        if ordered[0].min_days is not None:
            raise InvalidAgingPolicyError("first aging bucket must be unbounded below")
        if ordered[-1].max_days is not None:
            raise InvalidAgingPolicyError("last aging bucket must be unbounded above")
        for index, bucket in enumerate(ordered[:-1]):
            following = ordered[index + 1]
            if bucket.max_days is None:
                raise InvalidAgingPolicyError("only the final aging bucket may be unbounded above")
            if following.min_days is None:
                raise InvalidAgingPolicyError("only the first aging bucket may be unbounded below")
            if following.min_days != bucket.max_days + 1:
                raise InvalidAgingPolicyError(
                    "aging buckets must form a gap-free, non-overlapping integer partition"
                )

    def checksum(self) -> str:
        payload = {
            "policy_id": self.policy_id,
            "version": self.version,
            "date_basis": self.date_basis.value,
            "buckets": [
                {
                    "bucket_id": bucket.bucket_id,
                    "min_days": bucket.min_days,
                    "max_days": bucket.max_days,
                }
                for bucket in self.ordered_buckets
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class AgingSourceItem:
    source_item_id: str
    due_item_id: str
    entity_id: EntityId
    subledger_id: str
    party_id: str
    accounting_date: date
    due_date: date
    open_amount: Money

    def __post_init__(self) -> None:
        for name in ("source_item_id", "due_item_id", "subledger_id", "party_id"):
            if not getattr(self, name).strip():
                raise InvalidAgingSourceError(f"{name} must not be empty")
        if self.open_amount.amount <= 0:
            raise InvalidAgingSourceError("aging source open amount must be strictly positive")

    @classmethod
    def from_receivable(cls, receivable: Receivable, due_item: DueItem) -> AgingSourceItem:
        return cls._from_parent(
            source_item_id=receivable.receivable_id,
            entity_id=receivable.entity_id,
            subledger_id=receivable.subledger_id,
            party_id=receivable.party_id,
            accounting_date=receivable.accounting_date,
            due_items=receivable.due_items,
            due_item=due_item,
        )

    @classmethod
    def from_payable(cls, payable: Payable, due_item: DueItem) -> AgingSourceItem:
        return cls._from_parent(
            source_item_id=payable.payable_id,
            entity_id=payable.entity_id,
            subledger_id=payable.subledger_id,
            party_id=payable.party_id,
            accounting_date=payable.accounting_date,
            due_items=payable.due_items,
            due_item=due_item,
        )

    @classmethod
    def _from_parent(
        cls,
        *,
        source_item_id: str,
        entity_id: EntityId,
        subledger_id: str,
        party_id: str,
        accounting_date: date,
        due_items: tuple[DueItem, ...],
        due_item: DueItem,
    ) -> AgingSourceItem:
        if due_item not in due_items or due_item.source_subledger_item_id != source_item_id:
            raise InvalidAgingSourceError("due item does not belong to the aging source parent")
        require_same_entity(
            entity_id,
            due_item.entity_id,
            resource=f"aging due item {due_item.due_item_id}",
        )
        if due_item.open_amount.is_zero():
            raise InvalidAgingSourceError("fully settled due item is not an aging source")
        return cls(
            source_item_id=source_item_id,
            due_item_id=due_item.due_item_id,
            entity_id=entity_id,
            subledger_id=subledger_id,
            party_id=party_id,
            accounting_date=accounting_date,
            due_date=due_item.due_date,
            open_amount=due_item.open_amount,
        )


@dataclass(frozen=True, slots=True)
class AgingBucketResult:
    bucket_id: str
    total: Money
    source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AgingSnapshot:
    entity_id: EntityId
    subledger_id: str
    as_of: date
    currency: Currency
    policy_id: str
    policy_version: str
    policy_checksum: str
    source_ids: tuple[str, ...]
    buckets: tuple[AgingBucketResult, ...]
    total_open: Money
    checksum: str


class AgingEngine:
    """Partition eligible open subledger items exactly once according to a policy."""

    def snapshot(
        self,
        *,
        entity_id: EntityId,
        subledger_id: str,
        as_of: date,
        currency: Currency,
        policy: AgingPolicy,
        sources: tuple[AgingSourceItem, ...],
    ) -> AgingSnapshot:
        if not subledger_id.strip():
            raise InvalidAgingSourceError("aging subledger_id must not be empty")
        bucket_sources: dict[str, list[AgingSourceItem]] = {
            bucket.bucket_id: [] for bucket in policy.ordered_buckets
        }
        seen: set[str] = set()

        for source in sources:
            source_key = f"{source.source_item_id}:{source.due_item_id}"
            if source_key in seen:
                raise InvalidAgingSourceError(f"duplicate aging source {source_key!r}")
            seen.add(source_key)
            require_same_entity(entity_id, source.entity_id, resource=f"aging source {source_key}")
            if source.subledger_id != subledger_id:
                raise InvalidAgingSourceError("aging source belongs to a different subledger")
            if source.open_amount.currency != currency:
                raise InvalidAgingSourceError("aging source currency mismatch")
            if source.accounting_date > as_of:
                raise InvalidAgingSourceError("aging source accounting date cannot be after as_of")

            basis_date = (
                source.due_date
                if policy.date_basis is AgingDateBasis.DUE_DATE
                else source.accounting_date
            )
            age_days = (as_of - basis_date).days
            matches = tuple(bucket for bucket in policy.ordered_buckets if bucket.contains(age_days))
            if len(matches) != 1:
                raise InvalidAgingPolicyError(
                    f"aging policy must assign source {source_key!r} to exactly one bucket"
                )
            bucket_sources[matches[0].bucket_id].append(source)

        results: list[AgingBucketResult] = []
        total_open = Money.zero(currency)
        all_source_ids: list[str] = []
        for bucket in policy.ordered_buckets:
            total = Money.zero(currency)
            source_ids: list[str] = []
            for source in sorted(
                bucket_sources[bucket.bucket_id],
                key=lambda value: (value.due_date, value.source_item_id, value.due_item_id),
            ):
                total += source.open_amount
                source_ids.append(f"{source.source_item_id}:{source.due_item_id}")
            total_open += total
            all_source_ids.extend(source_ids)
            results.append(
                AgingBucketResult(
                    bucket_id=bucket.bucket_id,
                    total=total,
                    source_ids=tuple(source_ids),
                )
            )

        checksum = _snapshot_checksum(
            entity_id=entity_id,
            subledger_id=subledger_id,
            as_of=as_of,
            currency=currency,
            policy=policy,
            results=tuple(results),
        )
        return AgingSnapshot(
            entity_id=entity_id,
            subledger_id=subledger_id,
            as_of=as_of,
            currency=currency,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            policy_checksum=policy.checksum(),
            source_ids=tuple(sorted(all_source_ids)),
            buckets=tuple(results),
            total_open=total_open,
            checksum=checksum,
        )


def _snapshot_checksum(
    *,
    entity_id: EntityId,
    subledger_id: str,
    as_of: date,
    currency: Currency,
    policy: AgingPolicy,
    results: tuple[AgingBucketResult, ...],
) -> str:
    payload = {
        "entity_id": str(entity_id),
        "subledger_id": subledger_id,
        "as_of": as_of.isoformat(),
        "currency": str(currency.code),
        "policy_checksum": policy.checksum(),
        "buckets": [
            {
                "bucket_id": result.bucket_id,
                "total": str(result.total.amount),
                "source_ids": list(result.source_ids),
            }
            for result in results
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "AgingBucketDefinition",
    "AgingBucketResult",
    "AgingDateBasis",
    "AgingEngine",
    "AgingPolicy",
    "AgingSnapshot",
    "AgingSourceItem",
]
