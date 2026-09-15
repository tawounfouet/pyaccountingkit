"""Unit tests for the external valuation provider port (LOT-13)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.ports.valuation import (
    ValuationObservation,
    ValuationProvider,
    ValuationRequest,
)


class FakeValuationProvider:
    """Deterministic provider used to exercise the port contract."""

    def __init__(self, value: Decimal) -> None:
        self._value = value

    def get_value(self, request: ValuationRequest) -> ValuationObservation:
        return ValuationObservation(
            value=self._value,
            currency=request.currency,
            observed_at=datetime(2026, 6, 30, 12, 0, tzinfo=UTC),
            source="market-feed",
            source_reference=f"{request.subject_id}:{request.valuation_date.isoformat()}",
        )


def _request() -> ValuationRequest:
    return ValuationRequest(
        subject_id="asset:1",
        valuation_date=date(2026, 6, 30),
        currency=EUR,
    )


def test_provider_returns_traceable_observation() -> None:
    provider: ValuationProvider = FakeValuationProvider(Decimal("1500.00"))
    observation = provider.get_value(_request())
    assert observation.value == Decimal("1500.00")
    assert observation.source == "market-feed"
    assert observation.source_reference == "asset:1:2026-06-30"


def test_observation_rejects_negative_value() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ValuationObservation(
            value=Decimal("-1"),
            currency=EUR,
            observed_at=datetime(2026, 6, 30, tzinfo=UTC),
            source="market-feed",
        )


def test_observation_rejects_non_finite_value() -> None:
    with pytest.raises(ValueError, match="finite"):
        ValuationObservation(
            value=Decimal("NaN"),
            currency=EUR,
            observed_at=datetime(2026, 6, 30, tzinfo=UTC),
            source="market-feed",
        )
