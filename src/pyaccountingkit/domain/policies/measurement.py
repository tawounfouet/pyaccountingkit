"""Measurement domain: bases, policies, context and results (LOT-13).

A ``MeasurementPolicy`` determines how much an element should be booked.
It never posts directly (ADR-POL-007); it produces a ``MeasurementResult``
or ``MeasurementAdjustment`` which is consumed by a
``JournalEntryProposal`` (ADR-POL-008).  Initial and subsequent measurements
are distinct contracts (ADR-POL-004).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any

from pyaccountingkit.core.currency import Currency
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.policies.policy_set import PolicyType
from pyaccountingkit.domain.policies.policy_trace import PolicyExecutionTrace


class MeasurementBasis(StrEnum):
    """The measurement basis applied to an item (spec section 29)."""

    HISTORICAL_COST = "HISTORICAL_COST"
    REVALUED_COST = "REVALUED_COST"
    FAIR_VALUE = "FAIR_VALUE"
    AMORTIZED_COST = "AMORTIZED_COST"
    VALUE_IN_USE = "VALUE_IN_USE"
    NET_REALIZABLE_VALUE = "NET_REALIZABLE_VALUE"
    CURRENT_COST = "CURRENT_COST"
    CUSTOM = "CUSTOM"


class MeasurementPurpose(StrEnum):
    """Why a measurement is being performed."""

    INITIAL = "INITIAL"
    SUBSEQUENT = "SUBSEQUENT"
    DISCLOSURE = "DISCLOSURE"


class AdjustmentType(StrEnum):
    """Types of subsequent-measurement adjustments (spec section 37)."""

    DEPRECIATION = "DEPRECIATION"
    AMORTIZATION = "AMORTIZATION"
    IMPAIRMENT = "IMPAIRMENT"
    REVERSAL_OF_IMPAIRMENT = "REVERSAL_OF_IMPAIRMENT"
    REVALUATION = "REVALUATION"
    ACCRETION = "ACCRETION"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class MeasurementContext:
    """Immutable input of a measurement request (spec section 27)."""

    accounting_date: date
    functional_currency: Currency
    measurement_purpose: MeasurementPurpose
    policy_set_version: str
    reference_snapshot_id: str | None = None
    previous_measurement_id: str | None = None
    inputs: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MeasurementResult:
    """Outcome of a measurement (spec section 28)."""

    amount: Money
    measurement_basis: MeasurementBasis
    measurement_date: date
    inputs: Mapping[str, Any] = field(default_factory=dict)
    adjustments: tuple[MeasurementAdjustment, ...] = ()
    rounding: str = ""
    policy_trace: PolicyExecutionTrace | None = None


@dataclass(frozen=True, slots=True)
class MeasurementAdjustment:
    """A subsequent-measurement delta (spec section 37)."""

    adjustment_type: AdjustmentType
    previous_amount: Money
    new_amount: Money
    delta: Money
    accounting_date: date
    policy_trace: PolicyExecutionTrace | None = None

    def __post_init__(self) -> None:
        if not self.previous_amount.is_same_currency(self.new_amount):
            raise ValueError("adjustment amounts must share currency")
        if not self.delta.is_same_currency(self.new_amount):
            raise ValueError("delta must share currency with new amount")


class MeasurementPolicy(ABC):
    """Abstract base of every measurement policy (ADR-POL-003).

    A coded policy measures an item deterministically without mutating the
    ledger (ADR-POL-007).
    """

    policy_id: str = ""
    policy_version: str = ""
    policy_type: PolicyType = PolicyType.MEASUREMENT

    @abstractmethod
    def measure(
        self,
        *,
        subject: Any,
        context: MeasurementContext,
    ) -> MeasurementResult:
        """Compute the measurement result for a subject."""


class InitialMeasurementPolicy(MeasurementPolicy):
    """First measurement of a newly recognized element (ADR-POL-004)."""


class SubsequentMeasurementPolicy(MeasurementPolicy):
    """Re-measurement of an already-recognized item (ADR-POL-004)."""


__all__ = [
    "AdjustmentType",
    "InitialMeasurementPolicy",
    "MeasurementAdjustment",
    "MeasurementBasis",
    "MeasurementContext",
    "MeasurementPolicy",
    "MeasurementPurpose",
    "MeasurementResult",
    "SubsequentMeasurementPolicy",
]
