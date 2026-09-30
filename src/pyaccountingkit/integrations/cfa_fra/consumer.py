"""Framework-neutral bridge for the real CFA FRA Django consumer signatures.

This module intentionally uses duck typing for legacy ORM objects. It does not
import Django: the consumer passes its objects in, and only mapped canonical
identifiers cross the PyAccountingKit public boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import cast

from pyaccountingkit.integrations.cfa_fra.compatibility import (
    CFAFRAMigrationRouteError,
    DualRunComparator,
    DualRunObservation,
    LegacyCall,
    LegacyIdentityStoreProtocol,
    MigrationRouting,
    MutationBackend,
    ObservationSink,
    ReadBackend,
)
from pyaccountingkit.public.application import AccountingApplication
from pyaccountingkit.public.context import CommandContext


class CFAFRAConsumerMappingError(CFAFRAMigrationRouteError):
    """Raised when a legacy consumer object cannot be translated safely."""


ConsumerContextFactory = Callable[
    [object, Mapping[str, object] | None],
    CommandContext,
]


def _legacy_object_id(value: object) -> str:
    """Read a stable Django-like primary key without importing Django."""
    for attribute in ("pk", "id"):
        candidate = getattr(value, attribute, None)
        if candidate is not None and not callable(candidate):
            token = str(candidate).strip()
            if token:
                return token
    raise CFAFRAConsumerMappingError(
        f"legacy object {type(value).__name__!r} has no usable pk/id"
    )


class CFAFRADjangoConsumerBridge:
    """Preserve selected CFA FRA service signatures while delegating to the kit.

    This is a consumer migration bridge, not a permanent public API. Legacy
    objects are allowed only on the consumer side of this boundary.
    """

    __slots__ = (
        "_application",
        "_legacy_accounting",
        "_legacy_imports",
        "_legacy_reporting",
        "_routing",
        "_context_factory",
        "_identities",
        "_comparator",
        "_observation_sink",
    )

    def __init__(
        self,
        application: AccountingApplication,
        *,
        legacy_accounting: object | None,
        legacy_imports: object | None,
        legacy_reporting: object | None,
        routing: MigrationRouting,
        context_factory: ConsumerContextFactory,
        identities: LegacyIdentityStoreProtocol,
        comparator: DualRunComparator = lambda legacy, target: legacy == target,
        observation_sink: ObservationSink = lambda observation: None,
    ) -> None:
        self._application = application
        self._legacy_accounting = legacy_accounting
        self._legacy_imports = legacy_imports
        self._legacy_reporting = legacy_reporting
        self._routing = routing
        self._context_factory = context_factory
        self._identities = identities
        self._comparator = comparator
        self._observation_sink = observation_sink

    def post_journal_entry(
        self,
        *,
        entry: object,
        user: object,
        audit_metadata: Mapping[str, object] | None = None,
    ) -> object:
        """Preserve CFA FRA's historical posting service signature."""
        if self._routing.mutation_backend_for("post_entry") is MutationBackend.LEGACY:
            return self._legacy_call(
                self._legacy_accounting,
                "post_journal_entry",
                entry=entry,
                user=user,
                audit_metadata=audit_metadata,
            )

        entry_id = self._target_id("JournalEntry", entry)
        return self._application.entries.post(
            entry_id=entry_id,
            context=self._context_factory(user, audit_metadata),
        )

    def reverse_journal_entry(
        self,
        *,
        entry: object,
        user: object,
        posting_date: object,
        period: object,
        reason: str = "",
        audit_metadata: Mapping[str, object] | None = None,
    ) -> object:
        """Preserve CFA FRA reversal inputs while passing only IDs to the kit."""
        if self._routing.mutation_backend_for("reverse_entry") is MutationBackend.LEGACY:
            return self._legacy_call(
                self._legacy_accounting,
                "reverse_journal_entry",
                entry=entry,
                user=user,
                posting_date=posting_date,
                period=period,
                reason=reason,
                audit_metadata=audit_metadata,
            )

        entry_id = self._target_id("JournalEntry", entry)
        period_id = self._target_id("AccountingPeriod", period)
        return self._application.entries.reverse(
            entry_id=entry_id,
            target_period_id=period_id,
            reversal_date=posting_date,
            reason=reason,
            context=self._context_factory(user, audit_metadata),
        )

    def execute_fec_import(
        self,
        *,
        import_batch: object,
        user: object,
        audit_metadata: Mapping[str, object] | None = None,
    ) -> object:
        """Preserve CFA FRA's FEC execution signature with canonical batch identity."""
        if (
            self._routing.mutation_backend_for("execute_fec_import")
            is MutationBackend.LEGACY
        ):
            return self._legacy_call(
                self._legacy_imports,
                "execute_fec_import",
                import_batch=import_batch,
                user=user,
                audit_metadata=audit_metadata,
            )

        batch_id = self._target_id("FECImport", import_batch)
        return self._application.imports.execute(
            batch_id=batch_id,
            context=self._context_factory(user, audit_metadata),
        )

    def trial_balance_rows(
        self,
        *,
        organization: object,
        fiscal_year: object,
        as_of_date: object,
        variant: object = "ADJUSTED",
        query: str = "",
        include_zero: bool = False,
        user: object,
        audit_metadata: Mapping[str, object] | None = None,
    ) -> object:
        """Preserve the Sprint-5 selector shape during read-side migration."""
        legacy_parameters = {
            "organization": organization,
            "fiscal_year": fiscal_year,
            "as_of_date": as_of_date,
            "variant": variant,
            "query": query,
            "include_zero": include_zero,
        }
        backend = self._routing.read_backend_for("trial_balance")
        if "trial_balance" not in self._routing.dual_run_reads:
            if backend is ReadBackend.LEGACY:
                return self._legacy_call(
                    self._legacy_reporting,
                    "trial_balance_rows",
                    **legacy_parameters,
                )
            return self._target_trial_balance(
                organization=organization,
                fiscal_year=fiscal_year,
                as_of_date=as_of_date,
                variant=variant,
                query=query,
                include_zero=include_zero,
                user=user,
                audit_metadata=audit_metadata,
            )

        legacy_result = self._legacy_call(
            self._legacy_reporting,
            "trial_balance_rows",
            **legacy_parameters,
        )
        target_result = self._target_trial_balance(
            organization=organization,
            fiscal_year=fiscal_year,
            as_of_date=as_of_date,
            variant=variant,
            query=query,
            include_zero=include_zero,
            user=user,
            audit_metadata=audit_metadata,
        )
        self._observation_sink(
            DualRunObservation(
                operation="trial_balance",
                primary_backend=backend,
                matched=self._comparator(legacy_result, target_result),
            )
        )
        if backend is ReadBackend.LEGACY:
            return legacy_result
        return target_result

    def _target_trial_balance(
        self,
        *,
        organization: object,
        fiscal_year: object,
        as_of_date: object,
        variant: object,
        query: str,
        include_zero: bool,
        user: object,
        audit_metadata: Mapping[str, object] | None,
    ) -> object:
        entity_id = self._target_id("Organization", organization)
        fiscal_year_id = self._target_id("FiscalYear", fiscal_year)
        return self._application.ledger.trial_balance(
            entity_id=entity_id,
            fiscal_year_id=fiscal_year_id,
            as_of_date=as_of_date,
            variant=variant,
            query=query,
            include_zero=include_zero,
            context=self._context_factory(user, audit_metadata),
        )

    def _target_id(self, legacy_type: str, value: object) -> str:
        legacy_id = _legacy_object_id(value)
        link = self._identities.resolve(legacy_type, legacy_id)
        if link is None:
            raise CFAFRAConsumerMappingError(
                f"missing legacy identity mapping for {legacy_type}:{legacy_id}"
            )
        return link.target_id

    @staticmethod
    def _legacy_call(
        service: object | None,
        operation: str,
        **parameters: object,
    ) -> object:
        if service is None:
            raise CFAFRAMigrationRouteError(
                f"legacy CFA FRA service unavailable for {operation!r}"
            )
        candidate = getattr(service, operation, None)
        if not callable(candidate):
            raise CFAFRAMigrationRouteError(
                f"legacy CFA FRA operation {operation!r} is unavailable"
            )
        call = cast(LegacyCall, candidate)
        return call(**parameters)


__all__ = [
    "CFAFRAConsumerMappingError",
    "CFAFRADjangoConsumerBridge",
    "ConsumerContextFactory",
]
