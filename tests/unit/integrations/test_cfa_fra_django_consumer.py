"""LOT-26 tests for the real CFA FRA Django consumer bridge."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from pyaccountingkit import AccountingApplication, CommandContext
from pyaccountingkit.integrations.cfa_fra import (
    CFAFRAConsumerMappingError,
    CFAFRADjangoConsumerBridge,
    DualRunObservation,
    LegacyIdentityLink,
    LegacyIdentityMap,
    MigrationRouting,
    MutationBackend,
    ReadBackend,
)


@dataclass(frozen=True, slots=True)
class _LegacyObject:
    pk: str


@dataclass(frozen=True, slots=True)
class _User:
    pk: str


class _TargetService:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def post(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result

    def reverse(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result

    def execute(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result

    def trial_balance(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result


class _LegacyAccounting:
    def __init__(self) -> None:
        self.post_calls: list[dict[str, object]] = []
        self.reverse_calls: list[dict[str, object]] = []

    def post_journal_entry(self, **parameters: object) -> str:
        self.post_calls.append(parameters)
        return "legacy-posted"

    def reverse_journal_entry(self, **parameters: object) -> str:
        self.reverse_calls.append(parameters)
        return "legacy-reversed"


class _LegacyImports:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def execute_fec_import(self, **parameters: object) -> str:
        self.calls.append(parameters)
        return "legacy-imported"


class _LegacyReporting:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.result: object = "legacy-balance"

    def trial_balance_rows(self, **parameters: object) -> object:
        self.calls.append(parameters)
        return self.result


def _context(
    user: object,
    audit_metadata: object,
) -> CommandContext:
    assert isinstance(user, _User)
    metadata = dict(audit_metadata) if isinstance(audit_metadata, dict) else {}
    metadata["consumer"] = "cfa-fra"
    return CommandContext(
        actor=f"legacy-user:{user.pk}",
        correlation_id=f"consumer:{user.pk}",
        metadata=metadata,
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
                legacy_type="AccountingPeriod",
                legacy_id="period-legacy",
                target_type="AccountingPeriod",
                target_id="period-target",
            ),
            LegacyIdentityLink(
                legacy_type="FECImport",
                legacy_id="fec-legacy",
                target_type="AccountingImportBatch",
                target_id="batch-target",
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
        )
    )


def _bridge(
    routing: MigrationRouting,
    *,
    entry_result: object = "target-entry",
    import_result: object = "target-import",
    ledger_result: object = "target-balance",
    observations: list[DualRunObservation] | None = None,
) -> tuple[
    CFAFRADjangoConsumerBridge,
    _TargetService,
    _TargetService,
    _TargetService,
    _LegacyAccounting,
    _LegacyImports,
    _LegacyReporting,
]:
    entries = _TargetService(entry_result)
    imports = _TargetService(import_result)
    ledger = _TargetService(ledger_result)
    legacy_accounting = _LegacyAccounting()
    legacy_imports = _LegacyImports()
    legacy_reporting = _LegacyReporting()
    bridge = CFAFRADjangoConsumerBridge(
        AccountingApplication(entries=entries, imports=imports, ledger=ledger),
        legacy_accounting=legacy_accounting,
        legacy_imports=legacy_imports,
        legacy_reporting=legacy_reporting,
        routing=routing,
        context_factory=_context,
        identities=_identities(),
        comparator=lambda legacy, target: legacy == target,
        observation_sink=(observations if observations is not None else []).append,
    )
    return (
        bridge,
        entries,
        imports,
        ledger,
        legacy_accounting,
        legacy_imports,
        legacy_reporting,
    )


def test_post_journal_entry_maps_legacy_object_to_canonical_id_only() -> None:
    bridge, entries, _, _, legacy_accounting, _, _ = _bridge(
        MigrationRouting(
            mutation_routes={"post_entry": MutationBackend.PYACCOUNTINGKIT}
        )
    )
    entry = _LegacyObject("entry-legacy")

    result = bridge.post_journal_entry(
        entry=entry,
        user=_User("7"),
        audit_metadata={"request_id": "req-1"},
    )

    assert result == "target-entry"
    assert legacy_accounting.post_calls == []
    assert entries.calls == [
        {
            "entry_id": "entry-target",
            "context": CommandContext(
                actor="legacy-user:7",
                correlation_id="consumer:7",
                metadata={"request_id": "req-1", "consumer": "cfa-fra"},
            ),
        }
    ]
    assert entry not in entries.calls[0].values()


def test_legacy_post_keeps_exact_historical_signature_and_objects() -> None:
    bridge, entries, _, _, legacy_accounting, _, _ = _bridge(MigrationRouting())
    entry = _LegacyObject("entry-legacy")
    user = _User("8")

    result = bridge.post_journal_entry(
        entry=entry,
        user=user,
        audit_metadata={"ip": "127.0.0.1"},
    )

    assert result == "legacy-posted"
    assert entries.calls == []
    assert legacy_accounting.post_calls == [
        {
            "entry": entry,
            "user": user,
            "audit_metadata": {"ip": "127.0.0.1"},
        }
    ]


def test_reverse_maps_both_entry_and_period_before_public_call() -> None:
    bridge, entries, _, _, legacy_accounting, _, _ = _bridge(
        MigrationRouting(
            mutation_routes={"reverse_entry": MutationBackend.PYACCOUNTINGKIT}
        )
    )

    result = bridge.reverse_journal_entry(
        entry=_LegacyObject("entry-legacy"),
        user=_User("9"),
        posting_date=date(2026, 9, 30),
        period=_LegacyObject("period-legacy"),
        reason="Correction",
    )

    assert result == "target-entry"
    assert legacy_accounting.reverse_calls == []
    call = entries.calls[0]
    assert call["entry_id"] == "entry-target"
    assert call["target_period_id"] == "period-target"
    assert call["reversal_date"] == date(2026, 9, 30)
    assert call["reason"] == "Correction"


def test_execute_fec_import_uses_public_batch_id_contract() -> None:
    bridge, _, imports, _, _, legacy_imports, _ = _bridge(
        MigrationRouting(
            mutation_routes={"execute_fec_import": MutationBackend.PYACCOUNTINGKIT}
        )
    )

    result = bridge.execute_fec_import(
        import_batch=_LegacyObject("fec-legacy"),
        user=_User("10"),
    )

    assert result == "target-import"
    assert legacy_imports.calls == []
    assert imports.calls[0]["batch_id"] == "batch-target"
    assert "import_batch" not in imports.calls[0]


def test_missing_identity_fails_before_target_mutation() -> None:
    entries = _TargetService("target-entry")
    bridge = CFAFRADjangoConsumerBridge(
        AccountingApplication(entries=entries),
        legacy_accounting=_LegacyAccounting(),
        legacy_imports=None,
        legacy_reporting=None,
        routing=MigrationRouting(
            mutation_routes={"post_entry": MutationBackend.PYACCOUNTINGKIT}
        ),
        context_factory=_context,
        identities=LegacyIdentityMap(),
    )

    with pytest.raises(CFAFRAConsumerMappingError, match="JournalEntry:missing"):
        bridge.post_journal_entry(
            entry=_LegacyObject("missing"),
            user=_User("11"),
        )

    assert entries.calls == []


def test_trial_balance_dual_run_keeps_legacy_primary_and_maps_read_ids() -> None:
    observations: list[DualRunObservation] = []
    routing = MigrationRouting(
        read_routes={"trial_balance": ReadBackend.LEGACY},
        dual_run_reads=frozenset({"trial_balance"}),
    )
    (
        bridge,
        _,
        _,
        ledger,
        _,
        _,
        legacy_reporting,
    ) = _bridge(
        routing,
        ledger_result="legacy-balance",
        observations=observations,
    )
    organization = _LegacyObject("org-legacy")
    fiscal_year = _LegacyObject("fy-legacy")

    result = bridge.trial_balance_rows(
        organization=organization,
        fiscal_year=fiscal_year,
        as_of_date=date(2026, 9, 30),
        variant="ADJUSTED",
        query="512",
        include_zero=True,
        user=_User("12"),
    )

    assert result == "legacy-balance"
    assert legacy_reporting.calls[0]["organization"] is organization
    assert legacy_reporting.calls[0]["fiscal_year"] is fiscal_year
    assert ledger.calls[0]["entity_id"] == "entity-target"
    assert ledger.calls[0]["fiscal_year_id"] == "fy-target"
    assert organization not in ledger.calls[0].values()
    assert fiscal_year not in ledger.calls[0].values()
    assert observations == [
        DualRunObservation(
            operation="trial_balance",
            primary_backend=ReadBackend.LEGACY,
            matched=True,
        )
    ]


def test_consumer_object_without_primary_key_fails_closed() -> None:
    bridge, _, _, _, _, _, _ = _bridge(
        MigrationRouting(
            mutation_routes={"post_entry": MutationBackend.PYACCOUNTINGKIT}
        )
    )

    with pytest.raises(CFAFRAConsumerMappingError, match="no usable pk/id"):
        bridge.post_journal_entry(entry=object(), user=_User("13"))
