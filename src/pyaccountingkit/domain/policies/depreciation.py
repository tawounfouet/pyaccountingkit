"""Depreciation policy domain (LOT-13, foundation).

A ``DepreciationPolicy`` computes the periodic depreciation expense of an
asset (spec section 39).  It returns a ``DepreciationResult`` and never
touches the ledger (ADR-POL-007).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.policies.measurement import (
    MeasurementContext,
)
from pyaccountingkit.domain.policies.policy_set import PolicyType
from pyaccountingkit.domain.policies.policy_trace import PolicyExecutionTrace


class DepreciationMethod(StrEnum):
    """Depreciation allocation methods (spec section 40)."""

    STRAIGHT_LINE = "STRAIGHT_LINE"
    DECLINING_BALANCE = "DECLINING_BALANCE"
    UNITS_OF_PRODUCTION = "UNITS_OF_PRODUCTION"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class DepreciationResult:
    """Period outcome of a depreciation calculation (spec section 41)."""

    period_amount: Money
    cumulative_amount: Money
    carrying_amount_after: Money
    method: DepreciationMethod
    period_start: date | None = None
    period_end: date | None = None
    policy_trace: PolicyExecutionTrace | None = None


class DepreciationPolicy(ABC):
    """Abstract depreciation policy (spec section 39)."""

    policy_id: str = ""
    policy_version: str = ""
    policy_type: PolicyType = PolicyType.DEPRECIATION

    @abstractmethod
    def depreciate(
        self,
        *,
        depreciable_base: Money,
        residual_value: Money,
        useful_life_total: Decimal,
        cumulative_before: Money,
        period: tuple[date, date],
        context: MeasurementContext,
    ) -> DepreciationResult:
        """Compute one period of depreciation."""


@dataclass(frozen=True, slots=True)
class StraightLineDepreciationPolicy(DepreciationPolicy):
    """Equal-amount depreciation over useful life (spec section 40)."""

    policy_id: str = "dep-straight-line"
    policy_version: str = "1.0"

    def depreciate(
        self,
        *,
        depreciable_base: Money,
        residual_value: Money,
        useful_life_total: Decimal,
        cumulative_before: Money,
        period: tuple[date, date],
        context: MeasurementContext,
    ) -> DepreciationResult:
        if not depreciable_base.is_same_currency(residual_value):
            raise ValueError("base and residual must share currency")
        if useful_life_total <= 0:
            raise ValueError("useful life must be positive")
        recoverable = depreciable_base.amount - residual_value.amount
        period_amount = Money(recoverable / useful_life_total, depreciable_base.currency)
        cumulative_amt = cumulative_before.amount + period_amount.amount
        cumulative = Money(cumulative_amt, depreciable_base.currency)
        carrying = Money(depreciable_base.amount - cumulative.amount, depreciable_base.currency)
        return DepreciationResult(
            period_amount=period_amount,
            cumulative_amount=cumulative,
            carrying_amount_after=carrying,
            method=DepreciationMethod.STRAIGHT_LINE,
            period_start=period[0],
            period_end=period[1],
        )


__all__ = [
    "DepreciationMethod",
    "DepreciationPolicy",
    "DepreciationResult",
    "StraightLineDepreciationPolicy",
]
