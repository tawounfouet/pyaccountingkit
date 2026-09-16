"""Settlement allocation domain service and immutable allocation evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import StrEnum

from pyaccountingkit.core.entity_scope import require_same_entity
from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.subledgers.due_item import DueItem
from pyaccountingkit.domain.subledgers.errors import InvalidSettlementError, InvalidSubledgerItemError
from pyaccountingkit.domain.subledgers.payable import Payable
from pyaccountingkit.domain.subledgers.primitives import OperationalItemStatus
from pyaccountingkit.domain.subledgers.receivable import Receivable
from pyaccountingkit.domain.subledgers.settlement import Settlement

SubledgerItem = Receivable | Payable


class AllocationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REVERSED = "REVERSED"


@dataclass(frozen=True, slots=True)
class SettlementAllocation:
    allocation_id: str
    entity_id: EntityId
    settlement_id: str
    due_item_id: str
    source_item_id: str
    amount: Money
    allocation_date: date
    settlement_revision: int
    due_item_revision: int
    status: AllocationStatus = AllocationStatus.ACTIVE
    reversed_at: datetime | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("allocation_id", self.allocation_id),
            ("settlement_id", self.settlement_id),
            ("due_item_id", self.due_item_id),
            ("source_item_id", self.source_item_id),
        ):
            if not value.strip():
                raise InvalidSettlementError(f"{name} must not be empty")
        if self.amount.amount <= 0:
            raise InvalidSettlementError("allocation amount must be strictly positive")
        if self.settlement_revision <= 0 or self.due_item_revision <= 0:
            raise InvalidSettlementError("allocation must record post-transition revisions")
        if self.status is AllocationStatus.ACTIVE and self.reversed_at is not None:
            raise InvalidSettlementError("ACTIVE allocation cannot carry reversed_at")
        if self.status is AllocationStatus.REVERSED and self.reversed_at is None:
            raise InvalidSettlementError("REVERSED allocation requires reversed_at")

    def reversed(self, reversed_at: datetime) -> SettlementAllocation:
        if self.status is AllocationStatus.REVERSED:
            raise InvalidSettlementError(f"allocation {self.allocation_id!r} is already reversed")
        return replace(self, status=AllocationStatus.REVERSED, reversed_at=reversed_at)


@dataclass(frozen=True, slots=True)
class AllocationResult:
    settlement: Settlement
    subledger_item: SubledgerItem
    allocation: SettlementAllocation


class SettlementAllocationService:
    """Apply or reverse allocations without posting a second GL entry."""

    def allocate(
        self,
        *,
        allocation_id: str,
        settlement: Settlement,
        subledger_item: SubledgerItem,
        due_item_id: str,
        amount: Money,
        allocation_date: date,
        expected_settlement_revision: int | None = None,
        expected_due_item_revision: int | None = None,
    ) -> AllocationResult:
        self._validate_scope(settlement, subledger_item)
        due_item = _find_due_item(subledger_item, due_item_id)
        require_same_entity(
            settlement.entity_id,
            due_item.entity_id,
            resource=f"due item {due_item.due_item_id}",
        )
        if due_item.original_amount.currency != settlement.amount.currency:
            raise InvalidSettlementError("settlement and due item currencies must match")

        updated_due = due_item.allocate(amount, expected_revision=expected_due_item_revision)
        updated_settlement = settlement.allocate(
            amount,
            expected_revision=expected_settlement_revision,
        )
        updated_item = subledger_item.replace_due_item(updated_due)
        allocation = SettlementAllocation(
            allocation_id=allocation_id,
            entity_id=settlement.entity_id,
            settlement_id=settlement.settlement_id,
            due_item_id=due_item.due_item_id,
            source_item_id=_item_id(subledger_item),
            amount=amount,
            allocation_date=allocation_date,
            settlement_revision=updated_settlement.revision,
            due_item_revision=updated_due.revision,
        )
        return AllocationResult(
            settlement=updated_settlement,
            subledger_item=updated_item,
            allocation=allocation,
        )

    def reverse_allocation(
        self,
        *,
        settlement: Settlement,
        subledger_item: SubledgerItem,
        allocation: SettlementAllocation,
        reversed_at: datetime,
        expected_settlement_revision: int | None = None,
        expected_due_item_revision: int | None = None,
    ) -> AllocationResult:
        self._validate_scope(settlement, subledger_item)
        if allocation.status is AllocationStatus.REVERSED:
            raise InvalidSettlementError(f"allocation {allocation.allocation_id!r} is already reversed")
        if allocation.settlement_id != settlement.settlement_id:
            raise InvalidSettlementError("allocation belongs to a different settlement")
        if allocation.source_item_id != _item_id(subledger_item):
            raise InvalidSettlementError("allocation belongs to a different subledger item")
        require_same_entity(
            settlement.entity_id,
            allocation.entity_id,
            resource=f"allocation {allocation.allocation_id}",
        )
        due_item = _find_due_item(subledger_item, allocation.due_item_id)
        updated_due = due_item.restore(
            allocation.amount,
            expected_revision=expected_due_item_revision,
        )
        updated_settlement = settlement.restore_allocation(
            allocation.amount,
            expected_revision=expected_settlement_revision,
        )
        return AllocationResult(
            settlement=updated_settlement,
            subledger_item=subledger_item.replace_due_item(updated_due),
            allocation=allocation.reversed(reversed_at),
        )

    @staticmethod
    def _validate_scope(settlement: Settlement, subledger_item: SubledgerItem) -> None:
        require_same_entity(
            settlement.entity_id,
            subledger_item.entity_id,
            resource=f"subledger item {_item_id(subledger_item)}",
        )
        if settlement.subledger_id != subledger_item.subledger_id:
            raise InvalidSettlementError("settlement and item belong to different subledgers")
        if settlement.party_id is not None and settlement.party_id != subledger_item.party_id:
            raise InvalidSettlementError("settlement and item belong to different parties")
        if not subledger_item.accounting_effective:
            raise InvalidSubledgerItemError(
                "allocation requires an accounting-effective receivable/payable"
            )
        if subledger_item.operational_status is not OperationalItemStatus.OPEN:
            raise InvalidSubledgerItemError("allocation requires an OPEN receivable/payable")


def _item_id(item: SubledgerItem) -> str:
    if isinstance(item, Receivable):
        return item.receivable_id
    return item.payable_id


def _find_due_item(item: SubledgerItem, due_item_id: str) -> DueItem:
    for due_item in item.due_items:
        if due_item.due_item_id == due_item_id:
            return due_item
    raise InvalidSubledgerItemError(
        f"due item {due_item_id!r} is not part of subledger item {_item_id(item)!r}"
    )


__all__ = [
    "AllocationResult",
    "AllocationStatus",
    "SettlementAllocation",
    "SettlementAllocationService",
    "SubledgerItem",
]
