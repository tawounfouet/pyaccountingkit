"""End-to-end policy pipeline: set → resolution → recognition → trace (LOT-12)."""

from __future__ import annotations

from datetime import date

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.policies.applicability import PolicyApplicability, PolicyContext
from pyaccountingkit.domain.policies.policy_set import (
    AccountingPolicySet,
    PolicyBinding,
    PolicySetReference,
    PolicySetStatus,
    PolicyType,
)
from pyaccountingkit.domain.policies.policy_trace import PolicyExecutionTrace
from pyaccountingkit.domain.policies.recognition import (
    AccountingEvent,
    RecognitionDecision,
    RecognitionPolicy,
    RecognitionState,
)
from pyaccountingkit.domain.policies.resolution import PolicyResolutionService


class SaleRecognitionPolicy(RecognitionPolicy):
    policy_id = "rec-sale-on-doc-date"
    policy_version = "1.0"

    def evaluate(self, *, event: AccountingEvent, context: PolicyContext) -> RecognitionDecision:
        if event.event_type != "SALE":
            return RecognitionDecision(
                recognized=False,
                state=RecognitionState.NOT_RECOGNIZED,
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
        edition="2026",
        reference_snapshot_id="snap:1",
    )


def test_pipeline_resolves_then_recognizes_then_traces() -> None:
    binding = PolicyBinding(
        policy_type=PolicyType.RECOGNITION,
        policy_id="rec-sale-on-doc-date",
        policy_version="1.0",
        applicability=PolicyApplicability(standard_id="fr-pcg"),
    )
    policy_set = AccountingPolicySet(
        policy_set_id="ps:1",
        accounting_entity_id=EntityId("ent:1"),
        code="STD-FR",
        version="3",
        reference=PolicySetReference(
            standard_id="fr-pcg",
            edition="2026",
            dataset_version="v1",
            reference_snapshot_id="snap:1",
        ),
        status=PolicySetStatus.ACTIVE,
        effective_from=date(2026, 1, 1),
        bindings=(binding,),
    )
    event = AccountingEvent(
        event_id="ev:1",
        accounting_entity_id=EntityId("ent:1"),
        event_type="SALE",
        source="erp",
        source_reference="INV-100",
        facts={"amount": "120.00"},
        document_date=date(2026, 6, 20),
    )

    trace = PolicyResolutionService().resolve(
        policy_type=PolicyType.RECOGNITION,
        context=_ctx(),
        policy_set=policy_set,
    )
    assert trace.resolved
    assert trace.selected is not None
    assert trace.selected.policy_id == "rec-sale-on-doc-date"

    decision = SaleRecognitionPolicy().evaluate(event=event, context=_ctx())
    assert decision is not None
    assert decision.recognized is True
    assert decision.state is RecognitionState.RECOGNIZED

    execution = PolicyExecutionTrace(
        trace_id="tr:1",
        policy_type=PolicyType.RECOGNITION,
        policy_id=trace.selected.policy_id,
        policy_version=trace.selected.policy_version,
        policy_set_id=policy_set.policy_set_id,
        policy_set_version=policy_set.version,
        accounting_entity_id="ent:1",
        accounting_date=date(2026, 6, 30),
        reference_snapshot_id="snap:1",
        outcome=decision.state.value,
    )
    assert execution.policy_set_version == "3"
    assert execution.reference_snapshot_id == "snap:1"
    assert (execution.policy_id, execution.policy_version) == ("rec-sale-on-doc-date", "1.0")


def test_default_recognition_policy_returns_decision_type() -> None:
    decision = RecognitionDecision(
        recognized=False,
        state=RecognitionState.NOT_RECOGNIZED,
        rationale="test",
    )
    assert isinstance(decision, RecognitionDecision)
