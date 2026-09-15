"""External valuation provider port (LOT-13).

A ``ValuationProvider`` supplies market or appraisal observations.  The
measurement policy decides how the observation is used; the provider never
posts directly (ADR-POL-007).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol

from pyaccountingkit.core.currency import Currency


@dataclass(frozen=True, slots=True)
class ValuationRequest:
    """Input of a valuation request to a provider."""

    subject_id: str
    valuation_date: date
    currency: Currency
    measurement_basis: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ValuationObservation:
    """Output of a valuation provider (spec section 34)."""

    value: Decimal
    currency: Currency
    observed_at: datetime
    source: str
    source_reference: str = ""
    confidence: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.value.is_finite():
            raise ValueError("valuation value must be finite")
        if self.value < 0:
            raise ValueError("valuation value must be non-negative")


class ValuationProvider(Protocol):
    """Protocol for external valuation sources (spec section 33)."""

    def get_value(self, request: ValuationRequest) -> ValuationObservation: ...


__all__ = [
    "ValuationObservation",
    "ValuationProvider",
    "ValuationRequest",
]
