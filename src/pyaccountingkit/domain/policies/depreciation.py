"""Depreciation policy domain (LOT-13, hardened by LOT-QA-01).

A ``DepreciationPolicy`` computes the periodic depreciation expense of an
asset (spec section 39). It returns a ``DepreciationResult`` and never
touches the ledger (ADR-POL-007).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.policies.measurement import MeasurementContext
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
    """Equal full-period depreciation over useful life, capped at residual value."""

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
        if not depreciable_base.is_same_currency(cumulative_before):
            raise ValueError("base and cumulative depreciation must share currency")
        if depreciable_base.currency != context.functional_currency:
            raise ValueError("depreciation currency must match functional currency")
        if depreciable_base.amount < 0:
            raise ValueError("depreciable base must be non-negative")
        if residual_value.amount < 0:
            raise ValueError("residual value must be non-negative")
        if residual_value.amount > depreciable_base.amount:
            raise ValueError("residual value cannot exceed depreciable base")
        if useful_life_total <= 0:
            raise ValueError("useful life must be positive")
        if period[0] > period[1]:
            raise ValueError("depreciation period start must not follow period end")

        depreciable_amount = depreciable_base.amount - residual_value.amount
        if cumulative_before.amount < 0:
            raise ValueError("cumulative depreciation must be non-negative")
        if cumulative_before.amount > depreciable_amount:
            raise ValueError("cumulative depreciation cannot exceed depreciable amount")

        scheduled_amount = depreciable_amount / useful_life_total
        remaining_amount = depreciable_amount - cumulative_before.amount
        current_amount = min(scheduled_amount, remaining_amount)
        period_amount = Money(current_amount, depreciable_base.currency)
        cumulative = Money(
            cumulative_before.amount + period_amount.amount,
            depreciable_base.currency,
        )
        carrying = Money(
            depreciable_base.amount - cumulative.amount,
            depreciable_base.currency,
        )
        if carrying.amount < residual_value.amount:
            raise ValueError("depreciation cannot reduce carrying amount below residual value")

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
