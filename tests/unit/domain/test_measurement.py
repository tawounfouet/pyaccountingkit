"""Unit tests for the measurement domain (LOT-13 / LOT-QA-01)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.policies.measurement import (
    AdjustmentType,
    InitialMeasurementPolicy,
    MeasurementAdjustment,
    MeasurementBasis,
    MeasurementContext,
    MeasurementPolicy,
    MeasurementPurpose,
    MeasurementResult,
    SubsequentMeasurementPolicy,
)


class HistoricalCostPolicy(InitialMeasurementPolicy):
    """Demo initial policy: book the historical cost provided as input."""

    policy_id = "meas-historical-cost"
    policy_version = "1.0"

    def measure(self, *, subject: object, context: MeasurementContext) -> MeasurementResult:
        amount = Money(Decimal(str(context.inputs["historical_cost"])), context.functional_currency)
        return MeasurementResult(
            amount=amount,
            measurement_basis=MeasurementBasis.HISTORICAL_COST,
            measurement_date=context.accounting_date,
            inputs=dict(context.inputs),
        )


def _context() -> MeasurementContext:
    return MeasurementContext(
        accounting_date=date(2026, 6, 30),
        functional_currency=EUR,
        measurement_purpose=MeasurementPurpose.INITIAL,
        policy_set_version="3",
        reference_snapshot_id="snap:1",
        inputs={"historical_cost": "1200.00"},
    )


def test_measurement_bases_are_exposed() -> None:
    assert MeasurementBasis.HISTORICAL_COST.value == "HISTORICAL_COST"
    assert MeasurementBasis.FAIR_VALUE.value == "FAIR_VALUE"
    assert MeasurementBasis.AMORTIZED_COST.value == "AMORTIZED_COST"


def test_historical_cost_policy_measures_with_decimal() -> None:
    result = HistoricalCostPolicy().measure(subject=object(), context=_context())
    assert result.amount == Money.from_str("1200.00", EUR)
    assert isinstance(result.amount.amount, Decimal)
    assert result.measurement_basis is MeasurementBasis.HISTORICAL_COST
    assert result.measurement_date == date(2026, 6, 30)


def test_measurement_context_pins_policy_set_and_snapshot() -> None:
    context = _context()
    assert context.policy_set_version == "3"
    assert context.reference_snapshot_id == "snap:1"


def test_measurement_policy_is_abstract_and_never_posts() -> None:
    with pytest.raises(TypeError):
        MeasurementPolicy()  # type: ignore[abstract]
    assert not hasattr(MeasurementPolicy, "post")
    assert hasattr(MeasurementPolicy, "measure")


def test_initial_and_subsequent_are_distinct_contracts() -> None:
    assert issubclass(InitialMeasurementPolicy, MeasurementPolicy)
    assert issubclass(SubsequentMeasurementPolicy, MeasurementPolicy)
    assert InitialMeasurementPolicy is not SubsequentMeasurementPolicy


def test_adjustment_rejects_mixed_currencies() -> None:
    from pyaccountingkit.core.currency import USD

    with pytest.raises(ValueError, match="share currency"):
        MeasurementAdjustment(
            adjustment_type=AdjustmentType.DEPRECIATION,
            previous_amount=Money.from_str("100.00", EUR),
            new_amount=Money.from_str("90.00", USD),
            delta=Money.from_str("-10.00", EUR),
            accounting_date=date(2026, 6, 30),
        )


def test_adjustment_rejects_inconsistent_delta() -> None:
    with pytest.raises(ValueError, match="new_amount - previous_amount"):
        MeasurementAdjustment(
            adjustment_type=AdjustmentType.DEPRECIATION,
            previous_amount=Money.from_str("100.00", EUR),
            new_amount=Money.from_str("90.00", EUR),
            delta=Money.from_str("500.00", EUR),
            accounting_date=date(2026, 6, 30),
        )


def test_adjustment_accepts_consistent_currencies_and_delta() -> None:
    adjustment = MeasurementAdjustment(
        adjustment_type=AdjustmentType.DEPRECIATION,
        previous_amount=Money.from_str("100.00", EUR),
        new_amount=Money.from_str("90.00", EUR),
        delta=Money.from_str("-10.00", EUR),
        accounting_date=date(2026, 6, 30),
    )
    assert adjustment.delta.amount == Decimal("-10.00")


def test_measurement_result_is_immutable() -> None:
    result = HistoricalCostPolicy().measure(subject=object(), context=_context())
    with pytest.raises(AttributeError):
        result.amount = Money.from_str("0.00", EUR)  # type: ignore[misc]


def test_adjustment_type_values() -> None:
    assert AdjustmentType.IMPAIRMENT.value == "IMPAIRMENT"
    assert AdjustmentType.REVERSAL_OF_IMPAIRMENT.value == "REVERSAL_OF_IMPAIRMENT"
    assert MeasurementPurpose.SUBSEQUENT.value == "SUBSEQUENT"
