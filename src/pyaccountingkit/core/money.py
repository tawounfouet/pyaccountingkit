"""Exact decimal monetary value object.

``Money`` never uses IEEE 754 floats: amounts are ``decimal.Decimal`` values
quantized to the currency minor-unit exponent at construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.errors import IncompatibleCurrenciesError, InvalidAmountError


@dataclass(frozen=True, slots=True)
class Money:
    """Immutable monetary amount with an explicit currency."""

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise InvalidAmountError(f"Le montant doit être un Decimal, reçu: {type(self.amount)}")
        if not self.amount.is_finite():
            raise InvalidAmountError("Le montant doit être un nombre fini")
        quantized = self.amount.quantize(self.currency.subunit_exp, rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", quantized)

    @classmethod
    def from_str(cls, value: str, currency: Currency) -> Money:
        """Build a ``Money`` from a decimal string (never a float)."""
        return cls(Decimal(value), currency)

    @classmethod
    def zero(cls, currency: Currency) -> Money:
        """Build the neutral amount of ``currency``."""
        return cls(Decimal("0"), currency)

    def __add__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)

    def __mul__(self, factor: Decimal) -> Money:
        if not isinstance(factor, Decimal):
            raise InvalidAmountError(f"Le facteur doit être un Decimal, reçu: {type(factor)}")
        return Money(self.amount * factor, self.currency)

    __rmul__ = __mul__

    def is_zero(self) -> bool:
        return self.amount.is_zero()

    def is_same_currency(self, other: Money) -> bool:
        return self.currency == other.currency

    def compare(self, other: Money) -> int:
        """Ordering across currencies is forbidden without explicit conversion."""
        self._check_currency(other)
        return (self.amount > other.amount) - (self.amount < other.amount)

    def _check_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise IncompatibleCurrenciesError(
                f"Opération impossible entre {self.currency.code} et {other.currency.code}"
            )

    def __str__(self) -> str:
        return f"{self.amount} {self.currency.code}"


__all__ = ["Money"]
