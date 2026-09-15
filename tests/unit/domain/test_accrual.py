"""Unit tests for accrual / deferral / provision foundations (LOT-13)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.policies.accrual import (
    AccrualDecision,
    AccrualPolicy,
    AccrualResult,
    DeferralPolicy,
    DeferralResult,
    ProvisionMeasurementPolicy,
    ProvisionMeasurementResult,
    ProvisionRecognitionDecision,
    ProvisionRecognitionPolicy,
    ProvisionReviewAction,
)


class PeriodEndAccrualPolicy(AccrualPolicy):
    policy_id = "accr-period-end"
    policy_version = "1.0"

    def evaluate(
        self,
        *,
        transaction_date: date,
        invoice_date: date | None,
        period_start: date,
        period_end: date,
        estimated_amount: Money,
    ) -> AccrualResult:
        if invoice_date is not None and invoice_date <= period_end:
            return AccrualResult(
                decision=AccrualDecision.DO_NOT_RECOGNIZE,
                accrual_date=period_end,
                amount=estimated_amount,
                rationale="already invoiced in the period",
            )
        return AccrualResult(
            decision=AccrualDecision.RECOGNIZE,
            accrual_date=period_end,
            amount=estimated_amount,
            rationale="service delivered but not invoiced",
        )


class ThreeCriteriaProvisionPolicy(ProvisionRecognitionPolicy):
    policy_id = "prov-recognition"
    policy_version = "1.0"

    def decide(
        self,
        *,
        obligation: bool,
        probable_outflow: bool,
        reliable_estimate: bool,
        assessment_date: date,
        provision_type: str = "",
    ) -> ProvisionRecognitionDecision:
        recognized = obligation and probable_outflow and reliable_estimate
        return ProvisionRecognitionDecision(
            recognized=recognized,
            provision_date=assessment_date,
            provision_type=provision_type,
        )


class BestEstimateProvisionPolicy(ProvisionMeasurementPolicy):
    policy_id = "prov-measurement"
    policy_version = "1.0"

    def measure(
        self,
        *,
        best_estimate: Money,
        provision_date: date,
        previous_amount: Money | None = None,
    ) -> ProvisionMeasurementResult:
        action = ProvisionReviewAction.UNCHANGED
        if previous_amount is None:
            action = ProvisionReviewAction.INCREASE
        elif best_estimate.amount > previous_amount.amount:
            action = ProvisionReviewAction.INCREASE
        elif best_estimate.amount < previous_amount.amount:
            action = ProvisionReviewAction.DECREASE
        return ProvisionMeasurementResult(
            amount=best_estimate,
            measurement_date=provision_date,
            review_action=action,
        )


def test_accrual_recognized_before_invoicing() -> None:
    result = PeriodEndAccrualPolicy().evaluate(
        transaction_date=date(2026, 6, 20),
        invoice_date=None,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        estimated_amount=Money.from_str("500.00", EUR),
    )
    assert result.decision is AccrualDecision.RECOGNIZE
    assert result.amount == Money.from_str("500.00", EUR)


def test_accrual_skipped_when_invoiced() -> None:
    result = PeriodEndAccrualPolicy().evaluate(
        transaction_date=date(2026, 6, 20),
        invoice_date=date(2026, 6, 25),
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        estimated_amount=Money.from_str("500.00", EUR),
    )
    assert result.decision is AccrualDecision.DO_NOT_RECOGNIZE


def test_provision_requires_all_three_criteria() -> None:
    policy = ThreeCriteriaProvisionPolicy()
    recognized = policy.decide(
        obligation=True,
        probable_outflow=True,
        reliable_estimate=True,
        assessment_date=date(2026, 6, 30),
        provision_type="WARRANTY",
    )
    assert recognized.recognized is True
    missing = policy.decide(
        obligation=True,
        probable_outflow=False,
        reliable_estimate=True,
        assessment_date=date(2026, 6, 30),
    )
    assert missing.recognized is False


def test_provision_review_actions() -> None:
    policy = BestEstimateProvisionPolicy()
    first = policy.measure(
        best_estimate=Money.from_str("1000.00", EUR),
        provision_date=date(2026, 6, 30),
    )
    assert first.review_action is ProvisionReviewAction.INCREASE
    increased = policy.measure(
        best_estimate=Money.from_str("1200.00", EUR),
        provision_date=date(2026, 6, 30),
        previous_amount=Money.from_str("1000.00", EUR),
    )
    assert increased.review_action is ProvisionReviewAction.INCREASE
    decreased = policy.measure(
        best_estimate=Money.from_str("800.00", EUR),
        provision_date=date(2026, 6, 30),
        previous_amount=Money.from_str("1000.00", EUR),
    )
    assert decreased.review_action is ProvisionReviewAction.DECREASE
    unchanged = policy.measure(
        best_estimate=Money.from_str("1000.00", EUR),
        provision_date=date(2026, 6, 30),
        previous_amount=Money.from_str("1000.00", EUR),
    )
    assert unchanged.review_action is ProvisionReviewAction.UNCHANGED


def test_policies_are_abstract() -> None:
    with pytest.raises(TypeError):
        AccrualPolicy()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        DeferralPolicy()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        ProvisionRecognitionPolicy()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        ProvisionMeasurementPolicy()  # type: ignore[abstract]


def test_deferral_result_carries_window() -> None:
    result = DeferralResult(
        deferred_amount=Money.from_str("300.00", EUR),
        deferral_start=date(2026, 7, 1),
        deferral_end=date(2026, 12, 31),
    )
    assert result.deferral_end == date(2026, 12, 31)
