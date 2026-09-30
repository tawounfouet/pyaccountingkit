"""LOT-26 qualification for the CFA FRA legacy retirement gate."""

from __future__ import annotations

import pytest

from pyaccountingkit.integrations.cfa_fra import (
    LegacyRetirementBlockedError,
    LegacyRetirementEvidence,
    LegacyRetirementGate,
    MigrationRouting,
    MutationBackend,
    ReadBackend,
)


def _all_target_routing(*, dual_run: bool = False) -> MigrationRouting:
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
        dual_run_reads=frozenset({"trial_balance"}) if dual_run else frozenset(),
    )


def _green_evidence(**overrides: bool) -> LegacyRetirementEvidence:
    values = {
        "golden_parity_green": True,
        "production_adapters_green": True,
        "consumer_e2e_green": True,
        "identities_traceable": True,
        "regulatory_authority_replaced": True,
    }
    values.update(overrides)
    return LegacyRetirementEvidence(**values)


def test_retirement_is_blocked_while_any_route_remains_legacy() -> None:
    decision = LegacyRetirementGate().evaluate(
        MigrationRouting(),
        _green_evidence(),
    )

    assert decision.ready is False
    assert "mutation:post_entry:legacy" in decision.blockers
    assert "read:trial_balance:legacy" in decision.blockers


def test_retirement_is_blocked_while_shadow_dual_run_is_active() -> None:
    decision = LegacyRetirementGate().evaluate(
        _all_target_routing(dual_run=True),
        _green_evidence(),
    )

    assert decision.ready is False
    assert decision.blockers == ("read:trial_balance:dual-run-active",)


def test_retirement_is_blocked_when_consumer_e2e_is_not_green() -> None:
    routing = _all_target_routing()
    evidence = _green_evidence(consumer_e2e_green=False)

    with pytest.raises(LegacyRetirementBlockedError) as raised:
        LegacyRetirementGate().require_ready(routing, evidence)

    assert raised.value.blockers == ("evidence:consumer-e2e",)


def test_retirement_is_blocked_until_regulatory_authority_is_replaced() -> None:
    routing = _all_target_routing()
    evidence = _green_evidence(regulatory_authority_replaced=False)

    decision = LegacyRetirementGate().evaluate(routing, evidence)

    assert decision.ready is False
    assert decision.blockers == ("evidence:regulatory-authority",)


def test_retirement_is_allowed_only_after_routes_and_all_evidence_are_green() -> None:
    routing = _all_target_routing()
    decision = LegacyRetirementGate().evaluate(routing, _green_evidence())

    assert routing.remaining_legacy_mutations() == ()
    assert routing.remaining_legacy_reads() == ()
    assert decision.ready is True
    assert decision.blockers == ()
    LegacyRetirementGate().require_ready(routing, _green_evidence())
