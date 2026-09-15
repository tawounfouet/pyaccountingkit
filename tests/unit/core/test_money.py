"""Unit tests for the Money value object."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pyaccountingkit.core.currency import EUR, JPY, USD
from pyaccountingkit.core.errors import IncompatibleCurrenciesError, InvalidAmountError
from pyaccountingkit.core.money import Money


def test_money_rejects_float_amount() -> None:
    with pytest.raises(InvalidAmountError):
        Money(1.5, EUR)  # type: ignore[arg-type]


def test_money_rejects_non_finite_amount() -> None:
    with pytest.raises(InvalidAmountError):
        Money(Decimal("Infinity"), EUR)
    with pytest.raises(InvalidAmountError):
        Money(Decimal("NaN"), EUR)


def test_money_rounds_half_up_to_minor_unit() -> None:
    assert Money.from_str("0.005", EUR).amount == Decimal("0.01")
    assert Money.from_str("12.345", EUR).amount == Decimal("12.35")


def test_money_zero_is_quantized() -> None:
    assert Money.zero(EUR) == Money(Decimal("0"), EUR)


def test_money_addition_checks_currency() -> None:
    with pytest.raises(IncompatibleCurrenciesError):
        Money.zero(EUR) + Money.zero(USD)


def test_money_addition() -> None:
    assert Money.from_str("1.25", EUR) + Money.from_str("2.00", EUR) == Money.from_str("3.25", EUR)


def test_money_subtraction() -> None:
    assert Money.from_str("3.00", EUR) - Money.from_str("1.25", EUR) == Money.from_str("1.75", EUR)


def test_money_negation_preserves_currency() -> None:
    negated = -Money.from_str("1.25", EUR)
    assert negated.amount == Decimal("-1.25")
    assert negated.currency == EUR


def test_money_abs() -> None:
    assert abs(Money.from_str("-1.25", EUR)) == Money.from_str("1.25", EUR)


def test_money_scalar_multiplication() -> None:
    assert Money.from_str("1.10", EUR) * Decimal("3") == Money.from_str("3.30", EUR)


def test_money_scalar_must_be_decimal() -> None:
    with pytest.raises(InvalidAmountError):
        Money.zero(EUR) * 3


def test_money_is_zero() -> None:
    assert Money.zero(EUR).is_zero()
    assert not Money.from_str("0.01", EUR).is_zero()


def test_money_compare_requires_same_currency() -> None:
    with pytest.raises(IncompatibleCurrenciesError):
        Money.zero(EUR).compare(Money.zero(USD))


def test_money_compare_ordering() -> None:
    assert Money.from_str("2.00", EUR).compare(Money.from_str("1.00", EUR)) > 0
    assert Money.from_str("1.00", EUR).compare(Money.from_str("2.00", EUR)) < 0


def test_money_zero_exponent_currency() -> None:
    assert Money.from_str("100", JPY).amount == Decimal("100")
    assert Money.zero(JPY).amount == Decimal("0")


def test_money_is_immutable_after_construction() -> None:
    money = Money.from_str("1.00", EUR)
    with pytest.raises(AttributeError):
        money.amount = Decimal("9.99")  # type: ignore[misc]


def test_money_str() -> None:
    assert str(Money.from_str("1.50", EUR)) == "1.50 EUR"
