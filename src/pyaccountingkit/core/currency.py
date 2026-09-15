"""ISO 4217 currency value object with an explicit minor-unit exponent."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import NewType

from pyaccountingkit.core.errors import UnknownCurrencyError

CurrencyCode = NewType("CurrencyCode", str)

_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True, slots=True)
class Currency:
    """ISO 4217 currency identified by its three-letter code.

    ``exponent`` is the number of decimal places used by the minor unit
    (2 for the EUR, 0 for the XOF). ``subunit_exp`` is the exact Decimal
    used to quantize ``Money`` amounts.
    """

    code: CurrencyCode
    exponent: int = 2

    def __post_init__(self) -> None:
        if not _CODE_PATTERN.match(self.code):
            raise ValueError(f"Invalid ISO 4217 currency code: {self.code!r}")
        if not 0 <= self.exponent <= 4:
            raise ValueError(f"Invalid currency exponent: {self.exponent}")

    @property
    def subunit_exp(self) -> Decimal:
        """The Decimal exponent (e.g. ``Decimal('0.01')``) of the minor unit."""
        return Decimal(1).scaleb(-self.exponent)

    def __str__(self) -> str:
        return self.code


EUR = Currency(CurrencyCode("EUR"), exponent=2)
USD = Currency(CurrencyCode("USD"), exponent=2)
GBP = Currency(CurrencyCode("GBP"), exponent=2)
CHF = Currency(CurrencyCode("CHF"), exponent=2)
MAD = Currency(CurrencyCode("MAD"), exponent=2)
JPY = Currency(CurrencyCode("JPY"), exponent=0)
XOF = Currency(CurrencyCode("XOF"), exponent=0)
XAF = Currency(CurrencyCode("XAF"), exponent=0)

REGISTRY: dict[str, Currency] = {
    currency.code: currency for currency in (EUR, USD, GBP, CHF, MAD, JPY, XOF, XAF)
}


def lookup_currency(code: str) -> Currency:
    """Return the registered currency for ``code`` or raise ``UnknownCurrencyError``."""
    try:
        return REGISTRY[code]
    except KeyError as exc:
        raise UnknownCurrencyError(f"Unknown ISO 4217 currency code: {code!r}") from exc


__all__ = [
    "Currency",
    "CurrencyCode",
    "EUR",
    "USD",
    "GBP",
    "CHF",
    "MAD",
    "JPY",
    "XOF",
    "XAF",
    "REGISTRY",
    "lookup_currency",
]
