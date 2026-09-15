"""Unit tests for recognition domain (LOT-12)."""

from __future__ import annotations

from datetime import date

import pytest

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.policies.applicability import PolicyContext
from pyaccountingkit.domain.policies.recognition import (
    AccountingEvent,
    RecognitionDecision,
    RecognitionPolicy,
    RecognitionState,
)


class RecordRevenuePolicy(RecognitionPolicy):
    """Coded demonstration policy: recognize sales events on the document date."""

    policy_id = "rec-sale-on-doc-date"
    policy_version = "1.0"

    def evaluate(self, *, event: AccountingEvent, context: PolicyContext) -> RecognitionDecision:
        if event.event_type != "SALE":
            return RecognitionDecision(
                recognized=False,
                state=RecognitionState.NOT_RECOGNIZED,
                rationale="event type not recognized",
                policy_id=self.policy_id,
                policy_version=self.policy_version,
            )
        return RecognitionDecision(
            recognized=True,
            state=RecognitionState.RECOGNIZED,
            recognition_date=event.document_date or event.occurred_at or context.accounting_date,
            accounting_category="REVENUE",
            rationale="sale recognized on document date",
            evidence=("policy:rec-sale-on-doc-date:1.0",),
            policy_id=self.policy_id,
            policy_version=self.policy_version,
        )


def _ctx() -> PolicyContext:
    return PolicyContext(
        accounting_entity_id=EntityId("ent:1"),
        accounting_date=date(2026, 6, 30),
        standard_id="fr-pcg",
    )


def test_recognition_separate_from_measurement() -> None:
    # ADR-POL-003: RecognitionPolicy exposes evaluate(); a measurement policy
    # would expose measure(). The recognition contract carries no measurable
    # amount, keeping the two concerns decoupled at the type level.
    from pyaccountingkit.domain.policies.recognition import RecognitionPolicy as RP

    assert hasattr(RP, "evaluate")
    assert not hasattr(RP, "measure")


def test_recognize_sale_event() -> None:
    policy = RecordRevenuePolicy()
    event = AccountingEvent(
        event_id="ev:1",
        accounting_entity_id=EntityId("ent:1"),
        event_type="SALE",
        source="erp",
        source_reference="INV-100",
        facts={"amount": "120.00"},
        document_date=date(2026, 6, 20),
    )
    decision = policy.evaluate(event=event, context=_ctx())
    assert decision.recognized is True
    assert decision.state is RecognitionState.RECOGNIZED
    assert decision.recognition_date == date(2026, 6, 20)
    assert decision.accounting_category == "REVENUE"
    assert decision.policy_id == "rec-sale-on-doc-date"
    assert decision.policy_version == "1.0"


def test_not_recognized_other_event_type() -> None:
    policy = RecordRevenuePolicy()
    event = AccountingEvent(
        event_id="ev:2",
        accounting_entity_id=EntityId("ent:1"),
        event_type="PURCHASE",
        source="erp",
        source_reference="PO-7",
        facts={},
    )
    decision = policy.evaluate(event=event, context=_ctx())
    assert decision.recognized is False
    assert decision.state is RecognitionState.NOT_RECOGNIZED


def test_recognition_decision_rejects_contradiction() -> None:
    with pytest.raises(ValueError, match="state cannot be NOT_RECOGNIZED"):
        RecognitionDecision(
            recognized=True,
            state=RecognitionState.NOT_RECOGNIZED,
        )


def test_recognition_decision_immutable() -> None:
    decision = RecognitionDecision(
        recognized=True,
        state=RecognitionState.RECOGNIZED,
    )
    with pytest.raises(AttributeError):
        decision.recognized = False  # type: ignore[misc]


def test_recognition_policy_abstract() -> None:
    with pytest.raises(TypeError):
        RecognitionPolicy()  # type: ignore[abstract]


def test_requires_review_state_available() -> None:
    assert RecognitionState.REQUIRES_REVIEW.value == "REQUIRES_REVIEW"
    assert RecognitionState.DEFERRED.value == "DEFERRED"
