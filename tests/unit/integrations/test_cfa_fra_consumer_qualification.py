"""LOT-26 qualification tests for CFA FRA consumer cutover evidence."""

from __future__ import annotations

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    CFAFRAConsumerQualificationError,
    ConsumerQualification,
    ConsumerScenario,
    ConsumerScenarioEvidence,
    ConsumerScenarioStatus,
    LegacyRetirementEvidence,
    LegacyRetirementGate,
    MigrationRouting,
    MutationBackend,
    ReadBackend,
)


def _evidence(
    scenario: ConsumerScenario,
    status: ConsumerScenarioStatus = ConsumerScenarioStatus.PASS,
    *,
    detail: str | None = None,
) -> ConsumerScenarioEvidence:
    return ConsumerScenarioEvidence(
        scenario=scenario,
        status=status,
        source=f"cfa-fra-e2e::{scenario.value}",
        detail=detail,
        evidence_checksum=f"sha256:{scenario.value}",
    )


def _all_green_evidence() -> tuple[ConsumerScenarioEvidence, ...]:
    return tuple(_evidence(scenario) for scenario in ConsumerScenario)


def _all_target_routing() -> MigrationRouting:
    return MigrationRouting(
        mutation_routes={
            "post_entry": MutationBackend.PYACCOUNTINGKIT,
            "reverse_entry": MutationBackend.PYACCOUNTINGKIT,
            "execute_fec_import": MutationBackend.PYACCOUNTINGKIT,
            "close_period": MutationBackend.PYACCOUNTINGKIT,
        },
        read_routes={
            "trial_balance": ReadBackend.PYACCOUNTINGKIT,
            "financial_statements": ReadBackend.PYACCOUNTINGKIT,
            "run_controls": ReadBackend.PYACCOUNTINGKIT,
            "effective_plan": ReadBackend.PYACCOUNTINGKIT,
        },
    )


def test_consumer_qualification_requires_every_gate_consumer_scenario() -> None:
    qualification = ConsumerQualification(
        tuple(
            _evidence(scenario)
            for scenario in ConsumerScenario
            if scenario is not ConsumerScenario.CLOSING
        )
    )

    decision = qualification.evaluate()

    assert decision.green is False
    assert decision.missing == (ConsumerScenario.CLOSING,)
    assert decision.blockers == ("missing:closing",)


def test_consumer_qualification_distinguishes_failed_and_blocked_scenarios() -> None:
    evidence = list(_all_green_evidence())
    evidence[0] = _evidence(
        ConsumerScenario.LOGIN,
        ConsumerScenarioStatus.FAIL,
        detail="authentication regression",
    )
    closing_index = list(ConsumerScenario).index(ConsumerScenario.CLOSING)
    evidence[closing_index] = _evidence(
        ConsumerScenario.CLOSING,
        ConsumerScenarioStatus.BLOCKED,
        detail="Sprint 7 has no executable closing package",
    )

    decision = ConsumerQualification(tuple(evidence)).evaluate()

    assert decision.green is False
    assert decision.failed == (ConsumerScenario.LOGIN,)
    assert decision.blocked == (ConsumerScenario.CLOSING,)
    assert decision.blockers == ("blocked:closing", "failed:login")


def test_duplicate_consumer_evidence_fails_closed() -> None:
    item = _evidence(ConsumerScenario.LEDGER)

    with pytest.raises(CFAFRAConsumerQualificationError):
        ConsumerQualification((item, item))


def test_non_passing_evidence_requires_an_explanation() -> None:
    with pytest.raises(ValueError):
        ConsumerScenarioEvidence(
            scenario=ConsumerScenario.EXPORTS,
            status=ConsumerScenarioStatus.FAIL,
            source="consumer-e2e",
        )


def test_all_required_consumer_scenarios_produce_green_cutover_evidence() -> None:
    qualification = ConsumerQualification(_all_green_evidence())

    decision = qualification.evaluate()

    assert decision.green is True
    assert decision.blockers == ()
    assert decision.missing == ()
    qualification.require_green()


def test_retirement_gate_can_consume_cutover_green_state_without_bypassing_routes() -> None:
    qualification = ConsumerQualification(_all_green_evidence())
    consumer_green = qualification.evaluate().green

    decision = LegacyRetirementGate().evaluate(
        _all_target_routing(),
        LegacyRetirementEvidence(
            golden_parity_green=True,
            production_adapters_green=True,
            consumer_e2e_green=consumer_green,
            identities_traceable=True,
            regulatory_authority_replaced=True,
        ),
    )

    assert decision.ready is True
    assert decision.blockers == ()


def test_retirement_stays_blocked_when_consumer_cutover_is_not_green() -> None:
    qualification = ConsumerQualification(
        tuple(
            _evidence(scenario)
            for scenario in ConsumerScenario
            if scenario is not ConsumerScenario.EXPORTS
        )
    )

    decision = LegacyRetirementGate().evaluate(
        _all_target_routing(),
        LegacyRetirementEvidence(
            golden_parity_green=True,
            production_adapters_green=True,
            consumer_e2e_green=qualification.evaluate().green,
            identities_traceable=True,
            regulatory_authority_replaced=True,
        ),
    )

    assert decision.ready is False
    assert decision.blockers == ("evidence:consumer-e2e",)
