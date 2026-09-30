"""LOT-26 tests for CFA FRA financial-statement consumer conversion."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from pyaccountingkit import AccountingApplication, CommandContext
from pyaccountingkit.integrations.cfa_fra import (
    CFAFRAConsumerMappingError,
    CFAFRADjangoConsumerBridge,
    DualRunObservation,
    LegacyIdentityMap,
    MigrationRouting,
    ReadBackend,
    StatementTargetParametersFactory,
)


@dataclass(frozen=True, slots=True)
class _LegacyObject:
    pk: str


class _StatementsTarget:
    def __init__(self, result: object = "target-statement") -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def build(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result


class _LegacyStatements:
    def __init__(self, result: object = "legacy-statement") -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, object]]] = []

    def build_income_statement(self, **parameters: object) -> object:
        self.calls.append(("build_income_statement", parameters))
        return self.result

    def build_balance_sheet(self, **parameters: object) -> object:
        self.calls.append(("build_balance_sheet", parameters))
        return self.result

    def build_cash_flow_statement(self, **parameters: object) -> object:
        self.calls.append(("build_cash_flow_statement", parameters))
        return self.result


def _context(
    user: object,
    audit_metadata: object,
) -> CommandContext:
    metadata = dict(audit_metadata) if isinstance(audit_metadata, dict) else {}
    return CommandContext(
        actor="cfa-statement-consumer" if user is None else str(user),
        correlation_id="lot-26-statements",
        metadata=metadata,
    )


def _safe_parameters(
    statement: str,
    organization: object,
    fiscal_year: object,
    cutoff: object | None,
    include_comparative: bool,
) -> dict[str, object]:
    assert isinstance(organization, _LegacyObject)
    assert isinstance(fiscal_year, _LegacyObject)
    return {
        "entity_id": f"entity:{organization.pk}",
        "statement": statement,
        "source": {
            "trial_balance_snapshot_id": f"tb:{fiscal_year.pk}",
            "cutoff": cutoff,
        },
        "mapping_set": {"id": "mapping-v1"},
        "include_comparative": include_comparative,
    }


def _bridge(
    routing: MigrationRouting,
    *,
    target_result: object = "target-statement",
    legacy_result: object = "legacy-statement",
    observations: list[DualRunObservation] | None = None,
    parameter_factory: StatementTargetParametersFactory = _safe_parameters,
) -> tuple[CFAFRADjangoConsumerBridge, _StatementsTarget, _LegacyStatements]:
    target = _StatementsTarget(target_result)
    legacy = _LegacyStatements(legacy_result)
    bridge = CFAFRADjangoConsumerBridge(
        AccountingApplication(statements=target),
        legacy_accounting=None,
        legacy_imports=None,
        legacy_reporting=None,
        legacy_statements=legacy,
        routing=routing,
        context_factory=_context,
        identities=LegacyIdentityMap(),
        comparator=lambda legacy_value, target_value: legacy_value == target_value,
        observation_sink=(observations if observations is not None else []).append,
        statement_parameters_factory=parameter_factory,
    )
    return bridge, target, legacy


@pytest.mark.parametrize(
    ("method_name", "statement", "date_parameter"),
    (
        ("build_income_statement", "income_statement", "end_date"),
        ("build_balance_sheet", "balance_sheet", "as_of_date"),
        ("build_cash_flow_statement", "cash_flow", "end_date"),
    ),
)
def test_statement_target_route_preserves_signature_but_uses_explicit_public_inputs(
    method_name: str,
    statement: str,
    date_parameter: str,
) -> None:
    bridge, target, legacy = _bridge(
        MigrationRouting(
            read_routes={"financial_statements": ReadBackend.PYACCOUNTINGKIT}
        )
    )
    organization = _LegacyObject("org-1")
    fiscal_year = _LegacyObject("fy-2026")
    method = getattr(bridge, method_name)

    result = method(
        organization=organization,
        fiscal_year=fiscal_year,
        **{date_parameter: "2026-12-31"},
    )

    assert result == "target-statement"
    assert legacy.calls == []
    call = target.calls[0]
    assert call["statement"] == statement
    assert call["entity_id"] == "entity:org-1"
    assert call["mapping_set"] == {"id": "mapping-v1"}
    assert organization not in call.values()
    assert fiscal_year not in call.values()
    assert isinstance(call["context"], CommandContext)


def test_statement_legacy_route_preserves_original_objects_and_parameters() -> None:
    bridge, target, legacy = _bridge(MigrationRouting())
    organization = _LegacyObject("org-legacy")
    fiscal_year = _LegacyObject("fy-legacy")

    result = bridge.build_balance_sheet(
        organization=organization,
        fiscal_year=fiscal_year,
        as_of_date="2026-09-30",
        include_comparative=False,
    )

    assert result == "legacy-statement"
    assert target.calls == []
    assert legacy.calls == [
        (
            "build_balance_sheet",
            {
                "organization": organization,
                "fiscal_year": fiscal_year,
                "include_comparative": False,
                "as_of_date": "2026-09-30",
            },
        )
    ]


def test_statement_target_route_requires_explicit_parameter_factory() -> None:
    target = _StatementsTarget()
    bridge = CFAFRADjangoConsumerBridge(
        AccountingApplication(statements=target),
        legacy_accounting=None,
        legacy_imports=None,
        legacy_reporting=None,
        routing=MigrationRouting(
            read_routes={"financial_statements": ReadBackend.PYACCOUNTINGKIT}
        ),
        context_factory=_context,
        identities=LegacyIdentityMap(),
    )

    with pytest.raises(CFAFRAConsumerMappingError, match="parameter factory"):
        bridge.build_income_statement(
            organization=_LegacyObject("org"),
            fiscal_year=_LegacyObject("fy"),
        )

    assert target.calls == []


def test_statement_parameter_factory_cannot_leak_legacy_objects() -> None:
    def unsafe_factory(
        statement: str,
        organization: object,
        fiscal_year: object,
        cutoff: object | None,
        include_comparative: bool,
    ) -> dict[str, object]:
        del fiscal_year, cutoff, include_comparative
        return {
            "statement": statement,
            "source": {"legacy_organization": organization},
            "mapping_set": {"id": "mapping"},
        }

    bridge, target, _ = _bridge(
        MigrationRouting(
            read_routes={"financial_statements": ReadBackend.PYACCOUNTINGKIT}
        ),
        parameter_factory=unsafe_factory,
    )

    with pytest.raises(CFAFRAConsumerMappingError, match="leaked"):
        bridge.build_income_statement(
            organization=_LegacyObject("org"),
            fiscal_year=_LegacyObject("fy"),
        )

    assert target.calls == []


def test_statement_parameter_factory_cannot_override_context_or_statement_kind() -> None:
    def context_factory(
        statement: str,
        organization: object,
        fiscal_year: object,
        cutoff: object | None,
        include_comparative: bool,
    ) -> dict[str, object]:
        del organization, fiscal_year, cutoff, include_comparative
        return {
            "statement": statement,
            "source": {},
            "mapping_set": {},
            "context": object(),
        }

    bridge, _, _ = _bridge(
        MigrationRouting(
            read_routes={"financial_statements": ReadBackend.PYACCOUNTINGKIT}
        ),
        parameter_factory=context_factory,
    )
    with pytest.raises(CFAFRAConsumerMappingError, match="must not override"):
        bridge.build_income_statement(
            organization=_LegacyObject("org"),
            fiscal_year=_LegacyObject("fy"),
        )

    def wrong_statement_factory(
        statement: str,
        organization: object,
        fiscal_year: object,
        cutoff: object | None,
        include_comparative: bool,
    ) -> dict[str, object]:
        del statement, organization, fiscal_year, cutoff, include_comparative
        return {"statement": "balance_sheet", "source": {}, "mapping_set": {}}

    bridge, _, _ = _bridge(
        MigrationRouting(
            read_routes={"financial_statements": ReadBackend.PYACCOUNTINGKIT}
        ),
        parameter_factory=wrong_statement_factory,
    )
    with pytest.raises(CFAFRAConsumerMappingError, match="expected 'income_statement'"):
        bridge.build_income_statement(
            organization=_LegacyObject("org"),
            fiscal_year=_LegacyObject("fy"),
        )


def test_statement_dual_run_uses_shadow_only_and_returns_configured_primary() -> None:
    observations: list[DualRunObservation] = []
    bridge, target, legacy = _bridge(
        MigrationRouting(
            read_routes={"financial_statements": ReadBackend.LEGACY},
            dual_run_reads=frozenset({"financial_statements"}),
        ),
        target_result={"amount": "100"},
        legacy_result={"amount": "100"},
        observations=observations,
    )

    result = bridge.build_cash_flow_statement(
        organization=_LegacyObject("org"),
        fiscal_year=_LegacyObject("fy"),
        end_date="2026-12-31",
    )

    assert result == {"amount": "100"}
    assert len(target.calls) == 1
    assert len(legacy.calls) == 1
    assert observations == [
        DualRunObservation(
            operation="financial_statements",
            primary_backend=ReadBackend.LEGACY,
            matched=True,
        )
    ]
