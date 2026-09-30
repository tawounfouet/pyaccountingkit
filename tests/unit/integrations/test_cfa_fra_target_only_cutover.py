"""LOT-26 tests for the final target-only CFA FRA cutover profile."""

from __future__ import annotations

from dataclasses import dataclass

from pyaccountingkit import AccountingApplication, CommandContext
from pyaccountingkit.integrations.cfa_fra import (
    LegacyIdentityLink,
    LegacyIdentityMap,
    LegacyRetirementEvidence,
    LegacyRetirementGate,
    MigrationRouting,
    build_target_only_consumer_bridge,
)


@dataclass(frozen=True, slots=True)
class _LegacyObject:
    pk: str


class _Recorder:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def post(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result

    def trial_balance(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result

    def run(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result

    def close(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result

    def get_effective_plan(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result


def _context(
    user: object,
    audit_metadata: object,
) -> CommandContext:
    return CommandContext(
        actor="cutover-user" if user is None else str(user),
        correlation_id="lot-26-target-only",
        metadata=dict(audit_metadata) if isinstance(audit_metadata, dict) else {},
    )


def _identities() -> LegacyIdentityMap:
    return LegacyIdentityMap(
        (
            LegacyIdentityLink(
                legacy_type="JournalEntry",
                legacy_id="entry-legacy",
                target_type="JournalEntry",
                target_id="entry-target",
            ),
            LegacyIdentityLink(
                legacy_type="Organization",
                legacy_id="org-legacy",
                target_type="AccountingEntity",
                target_id="entity-target",
            ),
            LegacyIdentityLink(
                legacy_type="FiscalYear",
                legacy_id="fy-legacy",
                target_type="FiscalYear",
                target_id="fy-target",
            ),
            LegacyIdentityLink(
                legacy_type="AccountingPeriod",
                legacy_id="period-legacy",
                target_type="AccountingPeriod",
                target_id="period-target",
            ),
        )
    )


def test_target_only_routing_has_no_legacy_or_shadow_path() -> None:
    routing = MigrationRouting.target_only()

    assert routing.remaining_legacy_mutations() == ()
    assert routing.remaining_legacy_reads() == ()
    assert routing.dual_run_reads == frozenset()
    assert routing.is_target_only() is True


def test_target_only_bridge_executes_without_any_legacy_service_dependency() -> None:
    entries = _Recorder("posted")
    ledger = _Recorder("balance")
    controls = _Recorder("controls")
    closing = _Recorder("closed")
    references = _Recorder("plan")

    bridge = build_target_only_consumer_bridge(
        AccountingApplication(
            entries=entries,
            ledger=ledger,
            controls=controls,
            closing=closing,
            references=references,
        ),
        context_factory=_context,
        identities=_identities(),
        control_parameters_factory=lambda _organization, _fiscal_year: {
            "control_set": "YEAR_END",
            "scope": {"as_of": "2026-12-31"},
        },
        closing_parameters_factory=lambda _period: {
            "control_runs": ("control-1",),
            "trial_balance": {"checksum": "tb-1"},
        },
    )

    assert (
        bridge.post_journal_entry(
            entry=_LegacyObject("entry-legacy"),
            user="reviewer",
        )
        == "posted"
    )
    assert (
        bridge.trial_balance_rows(
            organization=_LegacyObject("org-legacy"),
            fiscal_year=_LegacyObject("fy-legacy"),
            as_of_date="2026-12-31",
            user="reviewer",
        )
        == "balance"
    )
    assert (
        bridge.run_controls(
            organization=_LegacyObject("org-legacy"),
            fiscal_year=_LegacyObject("fy-legacy"),
            user="reviewer",
        )
        == "controls"
    )
    assert (
        bridge.close_period(
            period=_LegacyObject("period-legacy"),
            user="reviewer",
        )
        == "closed"
    )
    assert (
        bridge.effective_plan(
            standard_id="SYSCOHADA",
            edition="2017",
            user="reviewer",
        )
        == "plan"
    )


def test_target_only_profile_is_retirement_ready_when_external_evidence_is_green() -> None:
    routing = MigrationRouting.target_only()

    decision = LegacyRetirementGate().evaluate(
        routing,
        LegacyRetirementEvidence(
            golden_parity_green=True,
            production_adapters_green=True,
            consumer_e2e_green=True,
            identities_traceable=True,
            regulatory_authority_replaced=True,
        ),
    )

    assert decision.ready is True
    assert decision.blockers == ()
