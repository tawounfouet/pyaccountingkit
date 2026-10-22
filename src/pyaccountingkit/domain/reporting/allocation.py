"""Conservative monetary allocation for reporting projections."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_DOWN, Decimal

from pyaccountingkit.core.money import Money


def allocate_money_conservatively(
    amount: Money,
    allocations: Sequence[tuple[str, Decimal]],
) -> dict[str, Money]:
    """Allocate one Money value without creating or losing a minor unit.

    Exact Decimal contributions are kept until final monetary materialization.
    Each provisional contribution is truncated toward zero at the currency
    minor unit. The remaining minor units are then assigned by largest
    fractional remainder, with the allocation key as deterministic tie-break.

    The result is independent from input order and sums exactly to the source.
    """
    if not allocations:
        raise ValueError("reporting allocation requires at least one target")

    keys = [key for key, _ in allocations]
    if len(keys) != len(set(keys)):
        raise ValueError("reporting allocation keys must be unique")
    if any(not key.strip() for key in keys):
        raise ValueError("reporting allocation keys must be non-empty")
    if any(weight <= 0 for _, weight in allocations):
        raise ValueError("reporting allocation weights must be strictly positive")

    total_weight = sum((weight for _, weight in allocations), Decimal("0"))
    if total_weight != Decimal("1"):
        raise ValueError(
            f"reporting allocation weights must sum exactly to 1, got {total_weight}"
        )

    unit = amount.currency.subunit_exp
    exact = {key: amount.amount * weight for key, weight in allocations}
    provisional = {
        key: value.quantize(unit, rounding=ROUND_DOWN)
        for key, value in exact.items()
    }

    provisional_total = sum(provisional.values(), Decimal("0"))
    residual = amount.amount - provisional_total
    residual_units_decimal = residual / unit
    integral_units = residual_units_decimal.to_integral_value()
    if residual_units_decimal != integral_units:
        raise ArithmeticError("reporting allocation residual is not a whole minor unit")

    residual_units = int(integral_units)
    if residual_units:
        ranked_keys = sorted(
            exact,
            key=lambda key: (-abs(exact[key] - provisional[key]), key),
        )
        if abs(residual_units) > len(ranked_keys):
            raise ArithmeticError("reporting allocation residual exceeds allocation targets")
        adjustment = unit if residual_units > 0 else -unit
        for key in ranked_keys[: abs(residual_units)]:
            provisional[key] += adjustment

    result = {
        key: Money(provisional[key], amount.currency)
        for key in sorted(provisional)
    }
    allocated_total = Money.zero(amount.currency)
    for value in result.values():
        allocated_total += value
    if allocated_total != amount:
        raise ArithmeticError(
            f"reporting allocation failed conservation: {allocated_total} != {amount}"
        )
    return result


__all__ = ["allocate_money_conservatively"]
