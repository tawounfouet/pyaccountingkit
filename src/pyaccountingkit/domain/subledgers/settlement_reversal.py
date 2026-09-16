"""Traceable settlement reversal that restores active allocations before reversal."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.accounting_reference import PostedAccountingReference
from pyaccountingkit.domain.subledgers.allocation import (
    AllocationStatus,
    SettlementAllocation,
    SettlementAllocationService,
    SubledgerItem,
)
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.errors import (
    AllocationConcurrencyConflictError,
    InvalidSettlementError,
    InvalidSubledgerItemError,
)
from pyaccountingkit.domain.subledgers.payable import Payable
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.settlement import Settlement


@dataclass(frozen=True, slots=True)
class SettlementReversal:
    reversal_id: str
    entity_id: EntityId
    settlement_id: str
    reversed_at: datetime
    reversed_allocation_ids: tuple[str, ...]
    accounting_reversal_reference: PostedAccountingReference
    reason: str

    def __post_init__(self) -> None:
        if not self.reversal_id.strip():
            raise InvalidSettlementError("reversal_id must not be empty")
        if not self.settlement_id.strip():
            raise InvalidSettlementError("settlement_id must not be empty")
        if not self.reason.strip():
            raise InvalidSettlementError("settlement reversal reason must not be empty")
        require_same_entity(
            self.entity_id,
            self.accounting_reversal_reference.entity_id,
            resource="settlement reversal accounting reference",
        )
        if len(set(self.reversed_allocation_ids)) != len(self.reversed_allocation_ids):
            raise InvalidSettlementError("reversed allocation ids must be unique")


@dataclass(frozen=True, slots=True)
class SettlementReversalResult:
    settlement: Settlement
    subledger_items: tuple[SubledgerItem, ...]
    allocations: tuple[SettlementAllocation, ...]
    reversal: SettlementReversal


class SettlementReversalService:
    """Restore active allocations and seal a settlement reversal as immutable evidence."""

    def __init__(self, allocation_service: SettlementAllocationService | None = None) -> None:
        self._allocation_service = allocation_service or SettlementAllocationService()

    def reverse(
        self,
        *,
        reversal_id: str,
        settlement: Settlement,
        subledger_items: tuple[SubledgerItem, ...],
        allocations: tuple[SettlementAllocation, ...],
        reversed_at: datetime,
        accounting_reversal_reference: PostedAccountingReference,
        reason: str,
        expected_settlement_revision: int | None = None,
        expected_due_item_revisions: Mapping[str, int] | None = None,
    ) -> SettlementReversalResult:
        require_same_entity(
            settlement.entity_id,
            accounting_reversal_reference.entity_id,
            resource="settlement reversal accounting reference",
        )
        if expected_settlement_revision is not None and (
            expected_settlement_revision != settlement.revision
        ):
            raise AllocationConcurrencyConflictError(
                f"settlement {settlement.settlement_id!r} revision {settlement.revision} "
                f"does not match expected revision {expected_settlement_revision}"
            )

        item_by_id = {_item_id(item): item for item in subledger_items}
        if len(item_by_id) != len(subledger_items):
            raise InvalidSubledgerItemError("subledger item ids must be unique during reversal")

        active = tuple(
            sorted(
                (
                    allocation
                    for allocation in allocations
                    if allocation.settlement_id == settlement.settlement_id
                    and allocation.status is AllocationStatus.ACTIVE
                ),
                key=lambda allocation: allocation.allocation_id,
            )
        )
        self._require_complete_allocation_set(settlement, active)
        self._validate_expected_due_revisions(
            item_by_id,
            active,
            expected_due_item_revisions or {},
        )

        working_settlement = settlement
        updated_allocations = list(allocations)
        reversed_ids: list[str] = []

        for allocation in active:
            item = item_by_id.get(allocation.source_item_id)
            if item is None:
                raise InvalidSubledgerItemError(
                    f"subledger item {allocation.source_item_id!r} required by allocation "
                    f"{allocation.allocation_id!r} is missing"
                )
            due_item = _due_item(item, allocation.due_item_id)
            result = self._allocation_service.reverse_allocation(
                settlement=working_settlement,
                subledger_item=item,
                allocation=allocation,
                reversed_at=reversed_at,
                expected_settlement_revision=working_settlement.revision,
                expected_due_item_revision=due_item.revision,
            )
            working_settlement = result.settlement
            item_by_id[allocation.source_item_id] = result.subledger_item
            allocation_index = updated_allocations.index(allocation)
            updated_allocations[allocation_index] = result.allocation
            reversed_ids.append(allocation.allocation_id)

        reversed_settlement = working_settlement.mark_reversed(
            reversal_id=reversal_id,
            accounting_reversal_reference=accounting_reversal_reference,
            expected_revision=working_settlement.revision,
        )
        reversal = SettlementReversal(
            reversal_id=reversal_id,
            entity_id=settlement.entity_id,
            settlement_id=settlement.settlement_id,
            reversed_at=reversed_at,
            reversed_allocation_ids=tuple(reversed_ids),
            accounting_reversal_reference=accounting_reversal_reference,
            reason=reason,
        )
        return SettlementReversalResult(
            settlement=reversed_settlement,
            subledger_items=tuple(item_by_id[_item_id(item)] for item in subledger_items),
            allocations=tuple(updated_allocations),
            reversal=reversal,
        )

    @staticmethod
    def _require_complete_allocation_set(
        settlement: Settlement,
        active_allocations: tuple[SettlementAllocation, ...],
    ) -> None:
        total = Money.zero(settlement.amount.currency)
        for allocation in active_allocations:
            require_same_entity(
                settlement.entity_id,
                allocation.entity_id,
                resource=f"allocation {allocation.allocation_id}",
            )
            if allocation.amount.currency != settlement.amount.currency:
                raise InvalidSettlementError("allocation currency must match settlement currency")
            total += allocation.amount
        if total != settlement.allocated_amount:
            raise InvalidSettlementError(
                "active allocations supplied for reversal must reconcile exactly to the "
                "settlement allocated amount"
            )

    @staticmethod
    def _validate_expected_due_revisions(
        item_by_id: Mapping[str, SubledgerItem],
        active_allocations: tuple[SettlementAllocation, ...],
        expected_revisions: Mapping[str, int],
    ) -> None:
        seen: set[tuple[str, str]] = set()
        for allocation in active_allocations:
            key = (allocation.source_item_id, allocation.due_item_id)
            if key in seen:
                continue
            seen.add(key)
            item = item_by_id.get(allocation.source_item_id)
            if item is None:
                continue
            due_item = _due_item(item, allocation.due_item_id)
            expected = expected_revisions.get(allocation.due_item_id)
            if expected is not None and expected != due_item.revision:
                raise AllocationConcurrencyConflictError(
                    f"due item {due_item.due_item_id!r} revision {due_item.revision} "
                    f"does not match expected revision {expected}"
                )


def _item_id(item: SubledgerItem) -> str:
    if isinstance(item, Receivable):
        return item.receivable_id
    return item.payable_id


def _due_item(item: SubledgerItem, due_item_id: str) -> DueItem:
    for due_item in item.due_items:
        if due_item.due_item_id == due_item_id:
            return due_item
    raise InvalidSubledgerItemError(
        f"due item {due_item_id!r} is not part of subledger item {_item_id(item)!r}"
    )


__all__ = [
    "SettlementReversal",
    "SettlementReversalResult",
    "SettlementReversalService",
]
