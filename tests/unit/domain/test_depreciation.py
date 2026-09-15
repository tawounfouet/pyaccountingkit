"""Unit tests for the depreciation policy foundation (LOT-13)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.policies.depreciation import (
    DepreciationMethod,
    DepreciationPolicy,
    DepreciationResult,
    StraightLineDepreciationPolicy,
)
from pyaccountingkit.domain.policies.measurement import MeasurementContext, MeasurementPurpose


def _context() -> MeasurementContext:
    return MeasurementContext(
        accounting_date=date(2026, 12, 31),
        functional_currency=EUR,
        measurement_purpose=MeasurementPurpose.SUBSEQUENT,
        policy_set_version="1",
    )


def test_straight_line_depreciates_evenly() -> None:
    policy = StraightLineDepreciationPolicy()
    result = policy.depreciate(
        depreciable_base=Money.from_str("12000.00", EUR),
        residual_value=Money.from_str("0.00", EUR),
        useful_life_total=Decimal("5"),
        cumulative_before=Money.zero(EUR),
        period=(date(2026, 1, 1), date(2026, 12, 31)),
        context=_context(),
    )
    assert result.period_amount == Money.from_str("2400.00", EUR)
    assert result.cumulative_amount == Money.from_str("2400.00", EUR)
    assert result.carrying_amount_after == Money.from_str("9600.00", EUR)
    assert result.method is DepreciationMethod.STRAIGHT_LINE


def test_straight_line_accounts_for_residual_and_cumulative() -> None:
    policy = StraightLineDepreciationPolicy()
    result = policy.depreciate(
        depreciable_base=Money.from_str("11000.00", EUR),
        residual_value=Money.from_str("1000.00", EUR),
        useful_life_total=Decimal("5"),
        cumulative_before=Money.from_str("2000.00", EUR),
        period=(date(2027, 1, 1), date(2027, 12, 31)),
        context=_context(),
    )
    assert result.period_amount == Money.from_str("2000.00", EUR)
    assert result.cumulative_amount == Money.from_str("4000.00", EUR)
    assert result.carrying_amount_after == Money.from_str("7000.00", EUR)


def test_straight_line_rejects_non_positive_life() -> None:
    with pytest.raises(ValueError, match="positive"):
        StraightLineDepreciationPolicy().depreciate(
            depreciable_base=Money.from_str("1000.00", EUR),
            residual_value=Money.zero(EUR),
            useful_life_total=Decimal("0"),
            cumulative_before=Money.zero(EUR),
            period=(date(2026, 1, 1), date(2026, 12, 31)),
            context=_context(),
        )


def test_depreciation_policy_is_abstract() -> None:
    with pytest.raises(TypeError):
        DepreciationPolicy()  # type: ignore[abstract]


def test_depreciation_result_immutable() -> None:
    result = DepreciationResult(
        period_amount=Money.from_str("10.00", EUR),
        cumulative_amount=Money.from_str("10.00", EUR),
        carrying_amount_after=Money.from_str("90.00", EUR),
        method=DepreciationMethod.STRAIGHT_LINE,
    )
    with pytest.raises(AttributeError):
        result.period_amount = Money.zero(EUR)  # type: ignore[misc]
