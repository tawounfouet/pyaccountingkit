"""Hypothesis property tests for Money arithmetic invariants (gate GC)."""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from pyaccountingkit.core.currency import EUR, USD
from pyaccountingkit.core.errors import IncompatibleCurrenciesError
from pyaccountingkit.core.money import Money

_money_amounts = st.integers(min_value=-(10**6), max_value=10**6).map(
    lambda value: Money(Decimal(value), EUR)
)


@given(_money_amounts, _money_amounts)
def test_addition_is_commutative(left: Money, right: Money) -> None:
    assert left + right == right + left


@given(_money_amounts, _money_amounts, _money_amounts)
def test_addition_is_associative(first: Money, second: Money, third: Money) -> None:
    assert (first + second) + third == first + (second + third)


@given(_money_amounts)
def test_zero_is_the_additive_identity(value: Money) -> None:
    assert value + Money.zero(EUR) == value
    assert Money.zero(EUR) + value == value


@given(_money_amounts)
def test_negation_is_the_inverse(value: Money) -> None:
    assert value + (-value) == Money.zero(EUR)


@given(_money_amounts, st.integers(min_value=0, max_value=100))
def test_scalar_multiplication_decomposes_as_repeated_addition(value: Money, scalar: int) -> None:
    assert value * Decimal(scalar) == sum((value for _ in range(scalar)), Money.zero(EUR))


@given(_money_amounts)
def test_construction_is_idempotent_within_a_currency(value: Money) -> None:
    rebuilt = Money(value.amount, EUR)
    assert rebuilt == value
    assert rebuilt.amount == value.amount


@given(_money_amounts)
def test_cross_currency_addition_is_forbidden(euro_amount: Money) -> None:
    try:
        euro_amount + Money.zero(USD)
        raise AssertionError("cross-currency addition must raise")
    except IncompatibleCurrenciesError:
        pass
