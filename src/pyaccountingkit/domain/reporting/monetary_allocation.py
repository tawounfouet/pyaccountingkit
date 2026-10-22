"""Conservative monetary allocation for reporting projections.

The reporting engines must never round each proportional contribution independently:
doing so can create or destroy minor units. This module keeps Decimal precision until
the allocation boundary, then distributes the unavoidable minor-unit residual with a
deterministic largest-remainder policy.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from pyaccountingkit.core.money import Money


def allocate_money_conservatively(
    source: Money,
    allocations: tuple[tuple[str, Decimal], ...],
) -> dict[str, Money]:
    """Allocate source exactly across weighted keys.

    Preconditions are intentionally strict because callers use versioned executable
    mapping sets: keys must be unique, weights must be positive Decimals, and the
    weights must sum exactly to one.

    Raw Decimal contributions are truncated toward zero at the currency minor unit,
    then remaining minor units are assigned to the largest fractional remainders.
    Ties are broken by allocation key so replay is independent of input ordering.
    """
    if not allocations:
        raise ValueError("monetary allocation requires at least one target")

    ordered = tuple(sorted(allocations, key=lambda item: item[0]))
    keys = tuple(key for key, _ in ordered)
    if len(keys) != len(set(keys)):
        raise ValueError("monetary allocation keys must be unique")

    for key, weight in ordered:
        if not key:
            raise ValueError("monetary allocation key must not be empty")
        if not isinstance(weight, Decimal):
            raise TypeError("monetary allocation weights must be Decimal values")
        if not weight.is_finite() or weight <= Decimal("0"):
            raise ValueError("monetary allocation weights must be finite and positive")

    total_weight = sum((weight for _, weight in ordered), Decimal("0"))
    if total_weight != Decimal("1"):
        raise ValueError(f"monetary allocation weights must sum exactly to 1, got {total_weight}")

    quantum = source.currency.subunit_exp
    raw = {key: source.amount * weight for key, weight in ordered}
    allocated = {key: amount.quantize(quantum, rounding=ROUND_DOWN) for key, amount in raw.items()}

    allocated_total = sum(allocated.values(), Decimal("0"))
    residual = source.amount - allocated_total
    if not residual.is_zero():
        residual_units_decimal = abs(residual / quantum)
        residual_units_integral = residual_units_decimal.to_integral_value()
        if residual_units_decimal != residual_units_integral:
            raise ArithmeticError("monetary allocation residual is not a whole minor unit")

        ranked_keys = tuple(
            key
            for key, _ in sorted(
                ordered,
                key=lambda item: (
                    -abs(raw[item[0]] - allocated[item[0]]),
                    item[0],
                ),
            )
        )
        step = quantum if residual > Decimal("0") else -quantum
        for index in range(int(residual_units_integral)):
            key = ranked_keys[index % len(ranked_keys)]
            allocated[key] += step

    result = {key: Money(allocated[key], source.currency) for key, _ in ordered}
    result_total = sum((value.amount for value in result.values()), Decimal("0"))
    if result_total != source.amount:
        raise ArithmeticError(
            f"monetary allocation must preserve source amount {source.amount}, got {result_total}"
        )
    return result


__all__ = ["allocate_money_conservatively"]
