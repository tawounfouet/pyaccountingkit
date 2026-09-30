"""LOT-26 tests for the CFA FRA strangler compatibility boundary."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from pyaccountingkit import AccountingApplication, CommandContext
from pyaccountingkit.integrations.cfa_fra import (
    CFAFRACompatibilityAdapter,
    CFAFRAMigrationRouteError,
    DualRunObservation,
    LegacyIdentityLink,
    LegacyIdentityMap,
    MigrationRouting,
    MutationBackend,
    ReadBackend,
)


class _RecordingService:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.calls: list[tuple[str, dict[str, object]]] = []

    def _record(self, operation: str, parameters: dict[str, object]) -> str:
        self.calls.append((operation, parameters))
        return f"{self.prefix}:{operation}"

    def post(self, **parameters: object) -> str:
        return self._record("post", parameters)

    def reverse(self, **parameters: object) -> str:
        return self._record("reverse", parameters)

    def execute(self, **parameters: object) -> str:
        return self._record("execute", parameters)

    def close(self, **parameters: object) -> str:
        return self._record("close", parameters)

    def trial_balance(self, **parameters: object) -> str:
        return self._record("trial_balance", parameters)

    def build(self, **parameters: object) -> str:
        return self._record("build", parameters)

    def run(self, **parameters: object) -> str:
        return self._record("run", parameters)

    def get_effective_plan(self, **parameters: object) -> str:
        return self._record("get_effective_plan", parameters)


class _LegacyService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.results: dict[str, object] = {}

    def _call(self, operation: str, parameters: dict[str, object]) -> object:
        self.calls.append((operation, parameters))
        return self.results.get(operation, f"legacy:{operation}")

    def post_entry(self, **parameters: object) -> object:
        return self._call("post_entry", parameters)

    def reverse_entry(self, **parameters: object) -> object:
        return self._call("reverse_entry", parameters)

    def execute_fec_import(self, **parameters: object) -> object:
        return self._call("execute_fec_import", parameters)

    def close_period(self, **parameters: object) -> object:
        return self._call("close_period", parameters)

    def trial_balance(self, **parameters: object) -> object:
        return self._call("trial_balance", parameters)

    def financial_statements(self, **parameters: object) -> object:
        return self._call("financial_statements", parameters)

    def run_controls(self, **parameters: object) -> object:
        return self._call("run_controls", parameters)

    def effective_plan(self, **parameters: object) -> object:
        return self._call("effective_plan", parameters)


@dataclass(frozen=True, slots=True)
class _User:
    pk: int


def _context(user: object) -> CommandContext:
    assert isinstance(user, _User)
    return CommandContext(
        actor=f"cfa-user:{user.pk}",
        correlation_id=f"migration:{user.pk}",
        metadata={"consumer": "cfa-fra"},
    )


def _application() -> tuple[AccountingApplication, dict[str, _RecordingService]]:
    services = {
        name: _RecordingService(name)
        for name in (
            "entries",
            "imports",
            "closing",
            "ledger",
            "statements",
            "controls",
            "references",
        )
    }
    return (
        AccountingApplication(
            entries=services["entries"],
            imports=services["imports"],
            closing=services["closing"],
            ledger=services["ledger"],
            statements=services["statements"],
            controls=services["controls"],
            references=services["references"],
        ),
        services,
    )


def test_mutation_switch_calls_pyaccountingkit_and_never_legacy() -> None:
    app, services = _application()
    legacy = _LegacyService()
    adapter = CFAFRACompatibilityAdapter(
        app,
        legacy_service=legacy,
        routing=MigrationRouting(
            mutation_routes={"post_entry": MutationBackend.PYACCOUNTINGKIT}
        ),
        context_factory=_context,
    )

    result = adapter.post_entry(entry_id="entry-42", user=_User(7))

    assert result == "entries:post"
    assert legacy.calls == []
    assert services["entries"].calls[0][0] == "post"
    assert services["entries"].calls[0][1]["entry_id"] == "entry-42"
    context = services["entries"].calls[0][1]["context"]
    assert isinstance(context, CommandContext)
    assert context.actor == "cfa-user:7"


def test_unspecified_mutation_stays_legacy_and_does_not_touch_target() -> None:
    app, services = _application()
    legacy = _LegacyService()
    adapter = CFAFRACompatibilityAdapter(
        app,
        legacy_service=legacy,
        routing=MigrationRouting(),
        context_factory=_context,
    )

    result = adapter.reverse_entry(entry_id="entry-42", user=_User(8))

    assert result == "legacy:reverse_entry"
    assert legacy.calls == [
        ("reverse_entry", {"entry_id": "entry-42", "user": _User(8)})
    ]
    assert services["entries"].calls == []


def test_dual_run_read_returns_legacy_primary_and_observes_target() -> None:
    app, services = _application()
    legacy = _LegacyService()
    legacy.results["trial_balance"] = {"balance": "100"}
    services["ledger"].prefix = "target"
    observations: list[DualRunObservation] = []

    adapter = CFAFRACompatibilityAdapter(
        app,
        legacy_service=legacy,
        routing=MigrationRouting(
            read_routes={"trial_balance": ReadBackend.LEGACY},
            dual_run_reads=frozenset({"trial_balance"}),
        ),
        context_factory=_context,
        comparator=lambda legacy_result, target_result: (
            legacy_result == {"balance": "100"}
            and target_result == "target:trial_balance"
        ),
        observation_sink=observations.append,
    )

    result = adapter.trial_balance(period_id="2026-09", user=_User(9))

    assert result == {"balance": "100"}
    assert len(legacy.calls) == 1
    assert services["ledger"].calls[0][0] == "trial_balance"
    assert observations == [
        DualRunObservation(
            operation="trial_balance",
            primary_backend=ReadBackend.LEGACY,
            matched=True,
        )
    ]


def test_dual_run_can_promote_target_without_changing_shadow_semantics() -> None:
    app, services = _application()
    legacy = _LegacyService()
    observations: list[DualRunObservation] = []
    adapter = CFAFRACompatibilityAdapter(
        app,
        legacy_service=legacy,
        routing=MigrationRouting(
            read_routes={"financial_statements": ReadBackend.PYACCOUNTINGKIT},
            dual_run_reads=frozenset({"financial_statements"}),
        ),
        context_factory=_context,
        comparator=lambda _legacy, _target: False,
        observation_sink=observations.append,
    )

    result = adapter.financial_statements(period_id="2026", user=_User(10))

    assert result == "statements:build"
    assert legacy.calls[0][0] == "financial_statements"
    assert services["statements"].calls[0][0] == "build"
    assert observations[0].matched is False
    assert observations[0].primary_backend is ReadBackend.PYACCOUNTINGKIT


def test_regulatory_effective_plan_delegates_to_public_reference_provider_boundary() -> None:
    app, services = _application()
    adapter = CFAFRACompatibilityAdapter(
        app,
        legacy_service=None,
        routing=MigrationRouting(
            read_routes={"effective_plan": ReadBackend.PYACCOUNTINGKIT}
        ),
        context_factory=_context,
    )

    result = adapter.effective_plan(
        user=_User(11),
        standard="SYSCOHADA",
        as_of="2026-01-01",
    )

    assert result == "references:get_effective_plan"
    assert services["references"].calls[0][1]["standard"] == "SYSCOHADA"


def test_missing_selected_legacy_route_fails_closed() -> None:
    app, _ = _application()
    adapter = CFAFRACompatibilityAdapter(
        app,
        legacy_service=None,
        routing=MigrationRouting(),
        context_factory=_context,
    )

    with pytest.raises(CFAFRAMigrationRouteError):
        adapter.close_period(period_id="2026-12", user=_User(12))


def test_legacy_identity_map_is_traceable_idempotent_and_conflict_safe() -> None:
    identities = LegacyIdentityMap()
    link = LegacyIdentityLink(
        legacy_type="JournalEntry",
        legacy_id="42",
        target_type="JournalEntry",
        target_id="entry-42",
        source_checksum="abc123",
    )

    assert identities.register(link) is link
    assert identities.register(link) is link
    assert identities.resolve("JournalEntry", "42") == link
    assert identities.snapshot() == (link,)

    with pytest.raises(CFAFRAMigrationRouteError):
        identities.register(
            LegacyIdentityLink(
                legacy_type="JournalEntry",
                legacy_id="42",
                target_type="JournalEntry",
                target_id="entry-other",
            )
        )
