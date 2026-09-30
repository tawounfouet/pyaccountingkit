"""LOT-26 tests for CFA FRA accounting-reference authority replacement."""

from __future__ import annotations

from pyaccountingkit import AccountingApplication, CommandContext
from pyaccountingkit.integrations.cfa_fra import (
    CFAFRADjangoConsumerBridge,
    CFAFRAMigrationRouteError,
    LegacyIdentityMap,
    MigrationRouting,
    ReadBackend,
)


class _ReferencesTarget:
    def __init__(self, result: object = "target-plan") -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def get_effective_plan(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result


def _context(
    user: object,
    audit_metadata: object,
) -> CommandContext:
    metadata = dict(audit_metadata) if isinstance(audit_metadata, dict) else {}
    return CommandContext(
        actor="cfa-reference-consumer" if user is None else str(user),
        correlation_id="lot-26-reference-authority",
        metadata=metadata,
    )


def _bridge(routing: MigrationRouting) -> tuple[CFAFRADjangoConsumerBridge, _ReferencesTarget]:
    target = _ReferencesTarget()
    bridge = CFAFRADjangoConsumerBridge(
        AccountingApplication(references=target),
        legacy_accounting=None,
        legacy_imports=None,
        legacy_reporting=None,
        routing=routing,
        context_factory=_context,
        identities=LegacyIdentityMap(),
    )
    return bridge, target


def test_effective_plan_delegates_to_canonical_reference_provider() -> None:
    bridge, target = _bridge(
        MigrationRouting(read_routes={"effective_plan": ReadBackend.PYACCOUNTINGKIT})
    )

    result = bridge.effective_plan(
        standard_id="syscohada",
        edition="2017",
        user="reviewer",
        audit_metadata={"source": "cfa-fra"},
    )

    assert result == "target-plan"
    assert len(target.calls) == 1
    call = target.calls[0]
    assert call["standard_id"] == "syscohada"
    assert call["edition"] == "2017"
    context = call["context"]
    assert isinstance(context, CommandContext)
    assert context.actor == "reviewer"
    assert context.metadata["source"] == "cfa-fra"


def test_effective_plan_legacy_authority_fails_closed_after_mig11() -> None:
    bridge, target = _bridge(MigrationRouting())

    try:
        bridge.effective_plan(standard_id="syscohada", edition="2017")
    except CFAFRAMigrationRouteError as exc:
        assert "local FrameworkAccount authority" in str(exc)
    else:
        raise AssertionError("legacy regulatory authority must fail closed")

    assert target.calls == []


def test_effective_plan_dual_run_is_forbidden_against_local_reference_tables() -> None:
    bridge, target = _bridge(
        MigrationRouting(
            read_routes={"effective_plan": ReadBackend.PYACCOUNTINGKIT},
            dual_run_reads=frozenset({"effective_plan"}),
        )
    )

    try:
        bridge.effective_plan(standard_id="syscohada", edition="2017")
    except CFAFRAMigrationRouteError as exc:
        assert "cannot dual-run" in str(exc)
    else:
        raise AssertionError("reference authority dual-run must fail closed")

    assert target.calls == []
