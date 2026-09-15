"""Unit tests for the inventory valuation foundation (LOT-13)."""

from __future__ import annotations

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.policies.inventory import (
    InventoryMethod,
    InventoryValuationPolicy,
    InventoryValuationResult,
)


class AverageCostInventoryPolicy(InventoryValuationPolicy):
    """Demo policy: value stock at the weighted average unit cost."""

    policy_id = "inv-weighted-average"
    policy_version = "1.0"

    def value(
        self,
        *,
        cost_total: Money,
        quantity: int,
        method: InventoryMethod = InventoryMethod.WEIGHTED_AVERAGE,
    ) -> InventoryValuationResult:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        return InventoryValuationResult(
            valued_amount=cost_total,
            method=method,
            quantity=quantity,
            unit_cost=Money(cost_total.amount / quantity, cost_total.currency),
        )


def test_weighted_average_computes_unit_cost() -> None:
    result = AverageCostInventoryPolicy().value(
        cost_total=Money.from_str("1000.00", EUR),
        quantity=4,
    )
    assert result.valued_amount == Money.from_str("1000.00", EUR)
    assert result.unit_cost == Money.from_str("250.00", EUR)
    assert result.method is InventoryMethod.WEIGHTED_AVERAGE


def test_inventory_policy_is_abstract() -> None:
    with pytest.raises(TypeError):
        InventoryValuationPolicy()  # type: ignore[abstract]


def test_inventory_methods_exposed() -> None:
    assert InventoryMethod.FIFO.value == "FIFO"
    assert InventoryMethod.SPECIFIC_IDENTIFICATION.value == "SPECIFIC_IDENTIFICATION"
