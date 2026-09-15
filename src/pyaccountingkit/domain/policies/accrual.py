"""Accrual, deferral and provision policy foundations (LOT-13).

Accruals and provisions decide whether — and at what amount — an expense,
revenue or risk belongs to the current period (spec sections 53-60).  All
policies here return decisions/results only; the actual posting is produced
by ``JournalEntryProposal`` and handled by the posting pipeline (ADR-POL-008).

Provision review distinguishes ``unchanged / increase / decrease / release``
(spec section 60); each change emits a new measurement and trace.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.policies.policy_set import PolicyType
from pyaccountingkit.domain.policies.policy_trace import PolicyExecutionTrace


class ProvisionReviewAction(StrEnum):
    """Outcome of a periodic provision review (spec section 60)."""

    UNCHANGED = "UNCHANGED"
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    RELEASE = "RELEASE"


class AccrualDecision(StrEnum):
    """Whether an expense/revenue should be recognized in the period."""

    RECOGNIZE = "RECOGNIZE"
    DO_NOT_RECOGNIZE = "DO_NOT_RECOGNIZE"


@dataclass(frozen=True, slots=True)
class AccrualResult:
    """Outcome of an accrual evaluation."""

    decision: AccrualDecision
    accrual_date: date
    amount: Money
    rationale: str = ""
    policy_trace: PolicyExecutionTrace | None = None


class AccrualPolicy(ABC):
    """Whether an unbilled expense/revenue belongs to the current period."""

    policy_id: str = ""
    policy_version: str = ""
    policy_type: PolicyType = PolicyType.ACCRUAL

    @abstractmethod
    def evaluate(
        self,
        *,
        transaction_date: date,
        invoice_date: date | None,
        period_start: date,
        period_end: date,
        estimated_amount: Money,
    ) -> AccrualResult:
        """Evaluate the accrual for one susceptible transaction."""


@dataclass(frozen=True, slots=True)
class DeferralResult:
    """Outcome of a deferral evaluation."""

    deferred_amount: Money
    deferral_start: date
    deferral_end: date
    rationale: str = ""
    policy_trace: PolicyExecutionTrace | None = None


class DeferralPolicy(ABC):
    """Whether an expense/revenue must be deferred to a later period."""

    policy_id: str = ""
    policy_version: str = ""
    policy_type: PolicyType = PolicyType.DEFERRAL

    @abstractmethod
    def evaluate(
        self,
        *,
        recognized_on: date,
        period_end: date,
        total_amount: Money,
        useful_until: date,
    ) -> DeferralResult:
        """Evaluate the amount and window of a deferral."""


@dataclass(frozen=True, slots=True)
class ProvisionRecognitionDecision:
    """Whether a provision must be recognized (spec section 58)."""

    recognized: bool
    provision_date: date
    provision_type: str = ""
    rationale: str = ""
    policy_trace: PolicyExecutionTrace | None = None


class ProvisionRecognitionPolicy(ABC):
    """Whether a provision should be recognized (spec section 58)."""

    policy_id: str = ""
    policy_version: str = ""
    policy_type: PolicyType = PolicyType.PROVISION_RECOGNITION

    @abstractmethod
    def decide(
        self,
        *,
        obligation: bool,
        probable_outflow: bool,
        reliable_estimate: bool,
        assessment_date: date,
        provision_type: str = "",
    ) -> ProvisionRecognitionDecision:
        """Decide recognition from the three recognition criteria."""


@dataclass(frozen=True, slots=True)
class ProvisionMeasurementResult:
    """At what amount a provision is booked (spec section 59)."""

    amount: Money
    measurement_date: date
    review_action: ProvisionReviewAction = ProvisionReviewAction.UNCHANGED
    rationale: str = ""
    policy_trace: PolicyExecutionTrace | None = None


class ProvisionMeasurementPolicy(ABC):
    """At what amount a provision is measured (spec section 59)."""

    policy_id: str = ""
    policy_version: str = ""
    policy_type: PolicyType = PolicyType.PROVISION_MEASUREMENT

    @abstractmethod
    def measure(
        self,
        *,
        best_estimate: Money,
        provision_date: date,
        previous_amount: Money | None = None,
    ) -> ProvisionMeasurementResult:
        """Measure the provision, detecting the review action."""


__all__ = [
    "AccrualDecision",
    "AccrualPolicy",
    "AccrualResult",
    "DeferralPolicy",
    "DeferralResult",
    "ProvisionMeasurementPolicy",
    "ProvisionMeasurementResult",
    "ProvisionRecognitionDecision",
    "ProvisionRecognitionPolicy",
    "ProvisionReviewAction",
]
