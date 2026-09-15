"""Unit tests for the impairment policy foundation (LOT-13)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from pyaccountingkit.core.currency import EUR
from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.policies.impairment import ImpairmentDecision, ImpairmentPolicy


class RecoverableValueImpairmentPolicy(ImpairmentPolicy):
    """Demo policy: impair down to a recoverable amount when it is lower."""

    policy_id = "imp-recoverable"
    policy_version = "1.0"

    def assess(
        self,
        *,
        carrying_amount: Money,
        recoverable_amount: Money | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ImpairmentDecision:
        if recoverable_amount is None or recoverable_amount.amount >= carrying_amount.amount:
            return ImpairmentDecision(
                impaired=False,
                carrying_amount_before=carrying_amount,
                recoverable_amount=recoverable_amount,
                carrying_amount_after=carrying_amount,
            )
        return ImpairmentDecision(
            impaired=True,
            carrying_amount_before=carrying_amount,
            recoverable_amount=recoverable_amount,
            impairment_amount=Money(
                carrying_amount.amount - recoverable_amount.amount,
                carrying_amount.currency,
            ),
            carrying_amount_after=recoverable_amount,
            reversal_allowed=True,
            rationale="recoverable value below carrying amount",
        )


def test_impairment_when_recoverable_is_lower() -> None:
    decision = RecoverableValueImpairmentPolicy().assess(
        carrying_amount=Money.from_str("1000.00", EUR),
        recoverable_amount=Money.from_str("700.00", EUR),
    )
    assert decision.impaired is True
    assert decision.impairment_amount == Money.from_str("300.00", EUR)
    assert decision.carrying_amount_after == Money.from_str("700.00", EUR)
    assert decision.reversal_allowed is True


def test_no_impairment_when_recoverable_is_higher() -> None:
    decision = RecoverableValueImpairmentPolicy().assess(
        carrying_amount=Money.from_str("1000.00", EUR),
        recoverable_amount=Money.from_str("1200.00", EUR),
    )
    assert decision.impaired is False
    assert decision.impairment_amount is None


def test_impairment_decision_immutable() -> None:
    decision = ImpairmentDecision(
        impaired=False,
        carrying_amount_before=Money.from_str("100.00", EUR),
    )
    with pytest.raises(AttributeError):
        decision.impaired = True  # type: ignore[misc]


def test_impairment_policy_is_abstract() -> None:
    with pytest.raises(TypeError):
        ImpairmentPolicy()  # type: ignore[abstract]
