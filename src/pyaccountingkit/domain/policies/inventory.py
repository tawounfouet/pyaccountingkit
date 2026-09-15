"""Inventory valuation policy foundation (LOT-13).

An ``InventoryValuationPolicy`` determines the carrying value of inventory
(spec sections 49-52).  The result feeds a ``JournalEntryProposal``; the
policy never posts directly (ADR-POL-007).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.policies.policy_set import PolicyType
from pyaccountingkit.domain.policies.policy_trace import PolicyExecutionTrace


class InventoryMethod(StrEnum):
    """Inventory cost-flow assumptions (spec section 51)."""

    FIFO = "FIFO"
    WEIGHTED_AVERAGE = "WEIGHTED_AVERAGE"
    SPECIFIC_IDENTIFICATION = "SPECIFIC_IDENTIFICATION"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class InventoryValuationResult:
    """Outcome of an inventory valuation (spec section 50)."""

    valued_amount: Money
    method: InventoryMethod
    quantity: int | None = None
    unit_cost: Money | None = None
    policy_trace: PolicyExecutionTrace | None = None


class InventoryValuationPolicy(ABC):
    """Abstract inventory valuation policy."""

    policy_id: str = ""
    policy_version: str = ""
    policy_type: PolicyType = PolicyType.INVENTORY_VALUATION

    @abstractmethod
    def value(
        self,
        *,
        cost_total: Money,
        quantity: int,
        method: InventoryMethod = InventoryMethod.FIFO,
    ) -> InventoryValuationResult:
        """Value an inventory position under a given method."""


__all__ = [
    "InventoryMethod",
    "InventoryValuationPolicy",
    "InventoryValuationResult",
]
