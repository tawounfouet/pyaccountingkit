"""LOT-28R / F16 corrective tests for conservative monetary allocation."""

from __future__ import annotations

from decimal import Decimal

from pyaccountingkit.core.currency import EUR, XAF
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.reporting.monetary_allocation import (
    allocate_money_conservatively,
)


def _total(values: dict[str, Money], *, currency=EUR) -> Money:
    return sum(values.values(), Money.zero(currency))


def test_half_cent_split_preserves_one_cent_exactly() -> None:
    source = Money.from_str("0.01", EUR)

    result = allocate_money_conservatively(
        source,
        (("a", Decimal("0.5")), ("b", Decimal("0.5"))),
    )

    assert result["a"] == Money.from_str("0.01", EUR)
    assert result["b"] == Money.zero(EUR)
    assert _total(result) == source


def test_negative_half_cent_split_preserves_sign_and_total() -> None:
    source = Money.from_str("-0.01", EUR)

    result = allocate_money_conservatively(
        source,
        (("a", Decimal("0.5")), ("b", Decimal("0.5"))),
    )

    assert result["a"] == Money.from_str("-0.01", EUR)
    assert result["b"] == Money.zero(EUR)
    assert _total(result) == source


def test_zero_decimal_currency_allocation_preserves_whole_unit() -> None:
    source = Money.from_str("1", XAF)

    result = allocate_money_conservatively(
        source,
        (
            ("a", Decimal("0.2")),
            ("b", Decimal("0.3")),
            ("c", Decimal("0.5")),
        ),
    )

    assert _total(result, currency=XAF) == source
    assert result["c"] == Money.from_str("1", XAF)


def test_allocation_is_independent_of_input_mapping_order() -> None:
    source = Money.from_str("0.01", EUR)
    forward = (
        ("a", Decimal("0.5")),
        ("b", Decimal("0.5")),
    )
    reverse = tuple(reversed(forward))

    assert allocate_money_conservatively(source, forward) == allocate_money_conservatively(
        source,
        reverse,
    )
