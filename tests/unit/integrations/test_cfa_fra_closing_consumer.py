"""LOT-26 tests for CFA FRA closing consumer conversion."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from pyaccountingkit import AccountingApplication, CommandContext
from pyaccountingkit.integrations.cfa_fra import (
    CFAFRAConsumerMappingError,
    CFAFRADjangoConsumerBridge,
    CFAFRAMigrationRouteError,
    ClosingTargetParametersFactory,
    LegacyIdentityLink,
    LegacyIdentityMap,
    MigrationRouting,
    MutationBackend,
)


@dataclass(frozen=True, slots=True)
class _LegacyObject:
    pk: str


class _ClosingTarget:
    def __init__(self, result: object = "target-closing") -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def close(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result


def _context(
    user: object,
    audit_metadata: object,
) -> CommandContext:
    metadata = dict(audit_metadata) if isinstance(audit_metadata, dict) else {}
    return CommandContext(
        actor="cfa-closing-consumer" if user is None else str(user),
        correlation_id="lot-26-closing",
        metadata=metadata,
    )


def _parameters(period: object) -> dict[str, object]:
    assert isinstance(period, _LegacyObject)
    return {
        "control_runs": ("control-run-1",),
        "trial_balance": {"checksum": "tb-checksum"},
        "next_period_id": "target-period-next",
        "opening_journal_id": "journal-opening",
        "opening_entry_id": "entry-opening",
        "opening_date": "2027-01-01",
    }


def _identities() -> LegacyIdentityMap:
    return LegacyIdentityMap(
        (
            LegacyIdentityLink(
                legacy_type="AccountingPeriod",
                legacy_id="period-2026-12",
                target_type="AccountingPeriod",
                target_id="target-period-2026-12",
            ),
        )
    )


def _bridge(
    *,
    routing: MigrationRouting,
    parameter_factory: ClosingTargetParametersFactory | None = _parameters,
) -> tuple[CFAFRADjangoConsumerBridge, _ClosingTarget]:
    target = _ClosingTarget()
    bridge = CFAFRADjangoConsumerBridge(
        AccountingApplication(closing=target),
        legacy_accounting=None,
        legacy_imports=None,
        legacy_reporting=None,
        routing=routing,
        context_factory=_context,
        identities=_identities(),
        closing_parameters_factory=parameter_factory,
    )
    return bridge, target


def test_closing_target_route_is_single_writer_and_uses_canonical_period_identity() -> None:
    bridge, target = _bridge(
        routing=MigrationRouting(mutation_routes={"close_period": MutationBackend.PYACCOUNTINGKIT})
    )
    period = _LegacyObject("period-2026-12")

    result = bridge.close_period(
        period=period,
        user="reviewer",
        audit_metadata={"source": "cfa-fra"},
    )

    assert result == "target-closing"
    call = target.calls[0]
    assert call["period_id"] == "target-period-2026-12"
    assert call["control_runs"] == ("control-run-1",)
    assert call["trial_balance"] == {"checksum": "tb-checksum"}
    assert period not in call.values()
    context = call["context"]
    assert isinstance(context, CommandContext)
    assert context.actor == "reviewer"
    assert context.metadata["source"] == "cfa-fra"


def test_closing_legacy_route_fails_closed_without_inventing_sprint7_service() -> None:
    bridge, target = _bridge(routing=MigrationRouting())

    with pytest.raises(CFAFRAMigrationRouteError, match="no executable closing service"):
        bridge.close_period(period=_LegacyObject("period-2026-12"))

    assert target.calls == []


def test_closing_target_route_requires_explicit_parameter_factory() -> None:
    bridge, target = _bridge(
        routing=MigrationRouting(mutation_routes={"close_period": MutationBackend.PYACCOUNTINGKIT}),
        parameter_factory=None,
    )

    with pytest.raises(CFAFRAConsumerMappingError, match="closing parameter factory"):
        bridge.close_period(period=_LegacyObject("period-2026-12"))

    assert target.calls == []


def test_closing_factory_cannot_override_context_or_canonical_period() -> None:
    def unsafe_context(period: object) -> dict[str, object]:
        del period
        return {"context": object()}

    bridge, _ = _bridge(
        routing=MigrationRouting(mutation_routes={"close_period": MutationBackend.PYACCOUNTINGKIT}),
        parameter_factory=unsafe_context,
    )
    with pytest.raises(CFAFRAConsumerMappingError, match="must not override"):
        bridge.close_period(period=_LegacyObject("period-2026-12"))

    def wrong_period(period: object) -> dict[str, object]:
        del period
        return {"period_id": "other-period"}

    bridge, _ = _bridge(
        routing=MigrationRouting(mutation_routes={"close_period": MutationBackend.PYACCOUNTINGKIT}),
        parameter_factory=wrong_period,
    )
    with pytest.raises(CFAFRAConsumerMappingError, match="expected 'target-period-2026-12'"):
        bridge.close_period(period=_LegacyObject("period-2026-12"))


def test_closing_factory_cannot_leak_legacy_period_object() -> None:
    def leaking_factory(period: object) -> dict[str, object]:
        return {
            "control_runs": (),
            "trial_balance": {"legacy_period": period},
        }

    bridge, target = _bridge(
        routing=MigrationRouting(mutation_routes={"close_period": MutationBackend.PYACCOUNTINGKIT}),
        parameter_factory=leaking_factory,
    )

    with pytest.raises(CFAFRAConsumerMappingError, match="leaked"):
        bridge.close_period(period=_LegacyObject("period-2026-12"))

    assert target.calls == []
