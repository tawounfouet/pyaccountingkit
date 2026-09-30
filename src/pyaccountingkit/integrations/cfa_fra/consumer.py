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
StatementTargetParametersFactory = Callable[
    [str, object, object, object | None, bool],
    Mapping[str, object],
]
ControlTargetParametersFactory = Callable[
    [object, object],
    Mapping[str, object],
]
ClosingTargetParametersFactory = Callable[
    [object],
    Mapping[str, object],
]


def _legacy_object_id(value: object) -> str:
    """Read a stable Django-like primary key without importing Django."""
    for attribute in ("pk", "id"):
        candidate = getattr(value, attribute, None)
        if candidate is not None and not callable(candidate):
            token = str(candidate).strip()
            if token:
                return token
    raise CFAFRAConsumerMappingError(f"legacy object {type(value).__name__!r} has no usable pk/id")


def build_target_only_consumer_bridge(
    application: AccountingApplication,
    *,
    context_factory: ConsumerContextFactory,
    identities: LegacyIdentityStoreProtocol,
    statement_parameters_factory: StatementTargetParametersFactory | None = None,
    control_parameters_factory: ControlTargetParametersFactory | None = None,
    closing_parameters_factory: ClosingTargetParametersFactory | None = None,
) -> CFAFRADjangoConsumerBridge:
    """Build the final CFA FRA cutover bridge with all legacy paths disabled."""
    return CFAFRADjangoConsumerBridge(
        application,
        legacy_accounting=None,
        legacy_imports=None,
        legacy_reporting=None,
        legacy_statements=None,
        routing=MigrationRouting.target_only(),
        context_factory=context_factory,
        identities=identities,
        statement_parameters_factory=statement_parameters_factory,
        control_parameters_factory=control_parameters_factory,
        closing_parameters_factory=closing_parameters_factory,
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
        "_legacy_statements",
        "_routing",
        "_context_factory",
        "_identities",
        "_comparator",
        "_observation_sink",
        "_statement_parameters_factory",
        "_control_parameters_factory",
        "_closing_parameters_factory",
    )

    def __init__(
        self,
        application: AccountingApplication,
        *,
        legacy_accounting: object | None,
        legacy_imports: object | None,
        legacy_reporting: object | None,
        legacy_statements: object | None = None,
        routing: MigrationRouting,
        context_factory: ConsumerContextFactory,
        identities: LegacyIdentityStoreProtocol,
        comparator: DualRunComparator = lambda legacy, target: legacy == target,
        observation_sink: ObservationSink = lambda observation: None,
        statement_parameters_factory: StatementTargetParametersFactory | None = None,
        control_parameters_factory: ControlTargetParametersFactory | None = None,
        closing_parameters_factory: ClosingTargetParametersFactory | None = None,
    ) -> None:
        self._application = application
        self._legacy_accounting = legacy_accounting
        self._legacy_imports = legacy_imports
        self._legacy_reporting = legacy_reporting
        self._legacy_statements = legacy_statements
        self._routing = routing
        self._context_factory = context_factory
        self._identities = identities
        self._comparator = comparator
        self._observation_sink = observation_sink
        self._statement_parameters_factory = statement_parameters_factory
        self._control_parameters_factory = control_parameters_factory
        self._closing_parameters_factory = closing_parameters_factory

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
        if self._routing.mutation_backend_for("execute_fec_import") is MutationBackend.LEGACY:
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

    def close_period(
        self,
        *,
        period: object,
        user: object | None = None,
        audit_metadata: Mapping[str, object] | None = None,
    ) -> object:
        """Delegate period close to PyAccountingKit as a single-writer mutation."""
        if self._routing.mutation_backend_for("close_period") is MutationBackend.LEGACY:
            raise CFAFRAMigrationRouteError(
                "frozen Sprint-7 CFA FRA has no executable closing service; "
                "close_period must be routed to PyAccountingKit"
            )

        factory = self._closing_parameters_factory
        if factory is None:
            raise CFAFRAConsumerMappingError(
                "target closing routing requires a closing parameter factory"
            )
        parameters = dict(factory(period))
        if "context" in parameters:
            raise CFAFRAConsumerMappingError(
                "closing parameter factory must not override CommandContext"
            )

        period_id = self._target_id("AccountingPeriod", period)
        configured_period = parameters.setdefault("period_id", period_id)
        if configured_period != period_id:
            raise CFAFRAConsumerMappingError(
                f"closing parameter factory returned period_id {configured_period!r}, "
                f"expected {period_id!r}"
            )

        self._reject_legacy_inputs(parameters, forbidden=(period,))
        return self._application.closing.close(
            **parameters,
            context=self._context_factory(user, audit_metadata),
        )

    def run_controls(
        self,
        *,
        organization: object,
        fiscal_year: object,
        user: object | None = None,
        audit_metadata: Mapping[str, object] | None = None,
    ) -> object:
        """Delegate Sprint-7 controls to PyAccountingKit without inventing a legacy engine."""
        backend = self._routing.read_backend_for("run_controls")
        if backend is ReadBackend.LEGACY:
            raise CFAFRAMigrationRouteError(
                "frozen Sprint-7 CFA FRA has no executable controls service; "
                "run_controls must be routed to PyAccountingKit"
            )
        if "run_controls" in self._routing.dual_run_reads:
            raise CFAFRAMigrationRouteError(
                "run_controls cannot dual-run because Sprint-7 has no executable legacy "
                "controls service"
            )

        factory = self._control_parameters_factory
        if factory is None:
            raise CFAFRAConsumerMappingError(
                "target controls routing requires a control parameter factory"
            )
        parameters = dict(factory(organization, fiscal_year))
        if "context" in parameters:
            raise CFAFRAConsumerMappingError(
                "control parameter factory must not override CommandContext"
            )

        entity_id = self._target_id("Organization", organization)
        fiscal_year_id = self._target_id("FiscalYear", fiscal_year)
        configured_entity = parameters.setdefault("entity_id", entity_id)
        configured_fiscal_year = parameters.setdefault("fiscal_year_id", fiscal_year_id)
        if configured_entity != entity_id:
            raise CFAFRAConsumerMappingError(
                f"control parameter factory returned entity_id {configured_entity!r}, "
                f"expected {entity_id!r}"
            )
        if configured_fiscal_year != fiscal_year_id:
            raise CFAFRAConsumerMappingError(
                "control parameter factory returned fiscal_year_id "
                f"{configured_fiscal_year!r}, expected {fiscal_year_id!r}"
            )

        self._reject_legacy_inputs(
            parameters,
            forbidden=(organization, fiscal_year),
        )
        return self._application.controls.run(
            **parameters,
            context=self._context_factory(user, audit_metadata),
        )

    def effective_plan(
        self,
        *,
        standard_id: str,
        edition: str,
        user: object | None = None,
        audit_metadata: Mapping[str, object] | None = None,
    ) -> object:
        """Replace CFA FRA local reference authority with the canonical provider."""
        backend = self._routing.read_backend_for("effective_plan")
        if backend is ReadBackend.LEGACY:
            raise CFAFRAMigrationRouteError(
                "CFA FRA local FrameworkAccount authority is not valid after MIG-11; "
                "effective_plan must be routed to PyAccountingKit"
            )
        if "effective_plan" in self._routing.dual_run_reads:
            raise CFAFRAMigrationRouteError(
                "effective_plan cannot dual-run against the local CFA FRA reference tables"
            )

        return self._application.references.get_effective_plan(
            standard_id=standard_id,
            edition=edition,
            context=self._context_factory(user, audit_metadata),
        )

    def build_income_statement(
        self,
        *,
        organization: object,
        fiscal_year: object,
        end_date: object | None = None,
        include_comparative: bool = True,
        user: object | None = None,
        audit_metadata: Mapping[str, object] | None = None,
    ) -> object:
        """Preserve the Sprint-6 income-statement service signature."""
        return self._statement_read(
            legacy_operation="build_income_statement",
            statement="income_statement",
            organization=organization,
            fiscal_year=fiscal_year,
            cutoff=end_date,
            cutoff_parameter="end_date",
            include_comparative=include_comparative,
            user=user,
            audit_metadata=audit_metadata,
        )

    def build_balance_sheet(
        self,
        *,
        organization: object,
        fiscal_year: object,
        as_of_date: object | None = None,
        include_comparative: bool = True,
        user: object | None = None,
        audit_metadata: Mapping[str, object] | None = None,
    ) -> object:
        """Preserve the Sprint-6 balance-sheet service signature."""
        return self._statement_read(
            legacy_operation="build_balance_sheet",
            statement="balance_sheet",
            organization=organization,
            fiscal_year=fiscal_year,
            cutoff=as_of_date,
            cutoff_parameter="as_of_date",
            include_comparative=include_comparative,
            user=user,
            audit_metadata=audit_metadata,
        )

    def build_cash_flow_statement(
        self,
        *,
        organization: object,
        fiscal_year: object,
        end_date: object | None = None,
        include_comparative: bool = True,
        user: object | None = None,
        audit_metadata: Mapping[str, object] | None = None,
    ) -> object:
        """Preserve the Sprint-6 cash-flow service signature."""
        return self._statement_read(
            legacy_operation="build_cash_flow_statement",
            statement="cash_flow",
            organization=organization,
            fiscal_year=fiscal_year,
            cutoff=end_date,
            cutoff_parameter="end_date",
            include_comparative=include_comparative,
            user=user,
            audit_metadata=audit_metadata,
        )

    def _statement_read(
        self,
        *,
        legacy_operation: str,
        statement: str,
        organization: object,
        fiscal_year: object,
        cutoff: object | None,
        cutoff_parameter: str,
        include_comparative: bool,
        user: object | None,
        audit_metadata: Mapping[str, object] | None,
    ) -> object:
        legacy_parameters: dict[str, object] = {
            "organization": organization,
            "fiscal_year": fiscal_year,
            "include_comparative": include_comparative,
        }
        if cutoff is not None:
            legacy_parameters[cutoff_parameter] = cutoff

        backend = self._routing.read_backend_for("financial_statements")
        if "financial_statements" not in self._routing.dual_run_reads:
            if backend is ReadBackend.LEGACY:
                return self._legacy_call(
                    self._legacy_statements,
                    legacy_operation,
                    **legacy_parameters,
                )
            return self._target_statement(
                statement=statement,
                organization=organization,
                fiscal_year=fiscal_year,
                cutoff=cutoff,
                include_comparative=include_comparative,
                user=user,
                audit_metadata=audit_metadata,
            )

        legacy_result = self._legacy_call(
            self._legacy_statements,
            legacy_operation,
            **legacy_parameters,
        )
        target_result = self._target_statement(
            statement=statement,
            organization=organization,
            fiscal_year=fiscal_year,
            cutoff=cutoff,
            include_comparative=include_comparative,
            user=user,
            audit_metadata=audit_metadata,
        )
        self._observation_sink(
            DualRunObservation(
                operation="financial_statements",
                primary_backend=backend,
                matched=self._comparator(legacy_result, target_result),
            )
        )
        if backend is ReadBackend.LEGACY:
            return legacy_result
        return target_result

    def _target_statement(
        self,
        *,
        statement: str,
        organization: object,
        fiscal_year: object,
        cutoff: object | None,
        include_comparative: bool,
        user: object | None,
        audit_metadata: Mapping[str, object] | None,
    ) -> object:
        factory = self._statement_parameters_factory
        if factory is None:
            raise CFAFRAConsumerMappingError(
                "target financial-statement routing requires a statement parameter factory"
            )
        parameters = dict(
            factory(
                statement,
                organization,
                fiscal_year,
                cutoff,
                include_comparative,
            )
        )
        if "context" in parameters:
            raise CFAFRAConsumerMappingError(
                "statement parameter factory must not override CommandContext"
            )
        configured_statement = parameters.setdefault("statement", statement)
        if configured_statement != statement:
            raise CFAFRAConsumerMappingError(
                f"statement parameter factory returned {configured_statement!r}, "
                f"expected {statement!r}"
            )
        self._reject_legacy_inputs(
            parameters,
            forbidden=(organization, fiscal_year),
        )
        return self._application.statements.build(
            **parameters,
            context=self._context_factory(user, audit_metadata),
        )

    @classmethod
    def _reject_legacy_inputs(
        cls,
        value: object,
        *,
        forbidden: tuple[object, ...],
    ) -> None:
        if any(value is item for item in forbidden):
            raise CFAFRAConsumerMappingError(
                "consumer parameter factory leaked a legacy consumer object"
            )
        if isinstance(value, Mapping):
            for item in value.values():
                cls._reject_legacy_inputs(item, forbidden=forbidden)
        elif isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                cls._reject_legacy_inputs(item, forbidden=forbidden)

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
            raise CFAFRAMigrationRouteError(f"legacy CFA FRA service unavailable for {operation!r}")
        candidate = getattr(service, operation, None)
        if not callable(candidate):
            raise CFAFRAMigrationRouteError(
                f"legacy CFA FRA operation {operation!r} is unavailable"
            )
        call = cast(LegacyCall, candidate)
        return call(**parameters)


__all__ = [
    "build_target_only_consumer_bridge",
    "CFAFRAConsumerMappingError",
    "CFAFRADjangoConsumerBridge",
    "ClosingTargetParametersFactory",
    "ConsumerContextFactory",
    "ControlTargetParametersFactory",
    "StatementTargetParametersFactory",
]
