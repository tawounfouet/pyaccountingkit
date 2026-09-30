"""LOT-26 tests for CFA FRA controls consumer conversion."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from pyaccountingkit import AccountingApplication, CommandContext
from pyaccountingkit.integrations.cfa_fra import (
    CFAFRAConsumerMappingError,
    CFAFRADjangoConsumerBridge,
    CFAFRAMigrationRouteError,
    ControlTargetParametersFactory,
    LegacyIdentityLink,
    LegacyIdentityMap,
    MigrationRouting,
    ReadBackend,
)


@dataclass(frozen=True, slots=True)
class _LegacyObject:
    pk: str


class _ControlsTarget:
    def __init__(self, result: object = "target-controls") -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def run(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result


def _context(
    user: object,
    audit_metadata: object,
) -> CommandContext:
    metadata = dict(audit_metadata) if isinstance(audit_metadata, dict) else {}
    return CommandContext(
        actor="cfa-controls-consumer" if user is None else str(user),
        correlation_id="lot-26-controls",
        metadata=metadata,
    )


def _parameters(
    organization: object,
    fiscal_year: object,
) -> dict[str, object]:
    assert isinstance(organization, _LegacyObject)
    assert isinstance(fiscal_year, _LegacyObject)
    return {
        "control_set": "YEAR_END",
        "scope": {"as_of": "2026-12-31"},
    }


def _identities() -> LegacyIdentityMap:
    return LegacyIdentityMap(
        (
            LegacyIdentityLink(
                legacy_type="Organization",
                legacy_id="org-1",
                target_type="AccountingEntity",
                target_id="entity-1",
            ),
            LegacyIdentityLink(
                legacy_type="FiscalYear",
                legacy_id="fy-2026",
                target_type="FiscalYear",
                target_id="target-fy-2026",
            ),
        )
    )


def _bridge(
    *,
    routing: MigrationRouting,
    parameter_factory: ControlTargetParametersFactory | None = _parameters,
) -> tuple[CFAFRADjangoConsumerBridge, _ControlsTarget]:
    target = _ControlsTarget()
    bridge = CFAFRADjangoConsumerBridge(
        AccountingApplication(controls=target),
        legacy_accounting=None,
        legacy_imports=None,
        legacy_reporting=None,
        routing=routing,
        context_factory=_context,
        identities=_identities(),
        control_parameters_factory=parameter_factory,
    )
    return bridge, target


def test_controls_target_route_maps_consumer_identity_and_never_leaks_orm_objects() -> None:
    bridge, target = _bridge(
        routing=MigrationRouting(read_routes={"run_controls": ReadBackend.PYACCOUNTINGKIT})
    )
    organization = _LegacyObject("org-1")
    fiscal_year = _LegacyObject("fy-2026")

    result = bridge.run_controls(
        organization=organization,
        fiscal_year=fiscal_year,
        user="reviewer",
        audit_metadata={"source": "cfa-fra"},
    )

    assert result == "target-controls"
    call = target.calls[0]
    assert call["entity_id"] == "entity-1"
    assert call["fiscal_year_id"] == "target-fy-2026"
    assert call["control_set"] == "YEAR_END"
    assert call["scope"] == {"as_of": "2026-12-31"}
    assert organization not in call.values()
    assert fiscal_year not in call.values()
    context = call["context"]
    assert isinstance(context, CommandContext)
    assert context.actor == "reviewer"
    assert context.metadata["source"] == "cfa-fra"


def test_controls_legacy_route_fails_closed_without_inventing_sprint7_service() -> None:
    bridge, target = _bridge(routing=MigrationRouting())

    with pytest.raises(CFAFRAMigrationRouteError, match="no executable controls service"):
        bridge.run_controls(
            organization=_LegacyObject("org-1"),
            fiscal_year=_LegacyObject("fy-2026"),
        )

    assert target.calls == []


def test_controls_dual_run_fails_closed_without_legacy_comparator_source() -> None:
    bridge, target = _bridge(
        routing=MigrationRouting(
            read_routes={"run_controls": ReadBackend.PYACCOUNTINGKIT},
            dual_run_reads=frozenset({"run_controls"}),
        )
    )

    with pytest.raises(CFAFRAMigrationRouteError, match="cannot dual-run"):
        bridge.run_controls(
            organization=_LegacyObject("org-1"),
            fiscal_year=_LegacyObject("fy-2026"),
        )

    assert target.calls == []


def test_controls_target_route_requires_explicit_parameter_factory() -> None:
    bridge, target = _bridge(
        routing=MigrationRouting(read_routes={"run_controls": ReadBackend.PYACCOUNTINGKIT}),
        parameter_factory=None,
    )

    with pytest.raises(CFAFRAConsumerMappingError, match="control parameter factory"):
        bridge.run_controls(
            organization=_LegacyObject("org-1"),
            fiscal_year=_LegacyObject("fy-2026"),
        )

    assert target.calls == []


def test_controls_factory_cannot_override_context_or_canonical_identity() -> None:
    def unsafe_context(
        organization: object,
        fiscal_year: object,
    ) -> dict[str, object]:
        del organization, fiscal_year
        return {"control_set": "YEAR_END", "context": object()}

    bridge, _ = _bridge(
        routing=MigrationRouting(read_routes={"run_controls": ReadBackend.PYACCOUNTINGKIT}),
        parameter_factory=unsafe_context,
    )
    with pytest.raises(CFAFRAConsumerMappingError, match="must not override"):
        bridge.run_controls(
            organization=_LegacyObject("org-1"),
            fiscal_year=_LegacyObject("fy-2026"),
        )

    def wrong_entity(
        organization: object,
        fiscal_year: object,
    ) -> dict[str, object]:
        del organization, fiscal_year
        return {"control_set": "YEAR_END", "entity_id": "other-entity"}

    bridge, _ = _bridge(
        routing=MigrationRouting(read_routes={"run_controls": ReadBackend.PYACCOUNTINGKIT}),
        parameter_factory=wrong_entity,
    )
    with pytest.raises(CFAFRAConsumerMappingError, match="expected 'entity-1'"):
        bridge.run_controls(
            organization=_LegacyObject("org-1"),
            fiscal_year=_LegacyObject("fy-2026"),
        )


def test_controls_factory_cannot_leak_legacy_objects() -> None:
    def leaking_factory(
        organization: object,
        fiscal_year: object,
    ) -> dict[str, object]:
        del fiscal_year
        return {
            "control_set": "YEAR_END",
            "scope": {"legacy_organization": organization},
        }

    bridge, target = _bridge(
        routing=MigrationRouting(read_routes={"run_controls": ReadBackend.PYACCOUNTINGKIT}),
        parameter_factory=leaking_factory,
    )

    with pytest.raises(CFAFRAConsumerMappingError, match="leaked"):
        bridge.run_controls(
            organization=_LegacyObject("org-1"),
            fiscal_year=_LegacyObject("fy-2026"),
        )

    assert target.calls == []
