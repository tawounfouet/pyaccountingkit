"""Unit tests for the Currency value object and ISO 4217 registry."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pyaccountingkit.core.currency import (
    EUR,
    JPY,
    Currency,
    CurrencyCode,
    lookup_currency,
)
from pyaccountingkit.core.errors import UnknownCurrencyError


def test_valid_currency_code() -> None:
    assert Currency(CurrencyCode("EUR"), exponent=2).code == "EUR"


@pytest.mark.parametrize("code", ["", "eur", "EU", "EURI", "123", "EUR1"])
def test_invalid_currency_codes_are_rejected(code: str) -> None:
    with pytest.raises(ValueError):
        Currency(CurrencyCode(code), exponent=2)


@pytest.mark.parametrize("exponent", [-1, 5])
def test_invalid_exponent_is_rejected(exponent: int) -> None:
    with pytest.raises(ValueError):
        Currency(CurrencyCode("ZZZ"), exponent=exponent)


def test_subunit_exponent_two_decimal_places() -> None:
    assert EUR.subunit_exp == Decimal("0.01")


@pytest.mark.parametrize("currency", [JPY])
def test_zero_exponent_currency_has_unit_subunit(currency: Currency) -> None:
    assert currency.subunit_exp == Decimal("1")


def test_lookup_registered_currency() -> None:
    assert lookup_currency("EUR") == EUR


def test_lookup_unknown_currency_raises() -> None:
    with pytest.raises(UnknownCurrencyError):
        lookup_currency("XXX")


def test_currency_is_frozen() -> None:
    with pytest.raises(AttributeError):
        EUR.exponent = 0  # type: ignore[misc]


def test_currency_str() -> None:
    assert str(EUR) == "EUR"
