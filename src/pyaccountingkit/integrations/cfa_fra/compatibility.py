"""Temporary CFA FRA consumer compatibility facade for LOT-26.

The adapter implements the strangler boundary documented by the migration map:
accounting mutations select exactly one backend, while selected read operations may
shadow both implementations for parity observation.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from pyaccountingkit.public.application import AccountingApplication
from pyaccountingkit.public.context import CommandContext


class CFAFRAMigrationRouteError(RuntimeError):
    """Raised when a configured CFA FRA migration route cannot be executed."""


class MutationBackend(StrEnum):
    """Exclusive backend for a state-changing CFA FRA operation."""

    LEGACY = "LEGACY"
    PYACCOUNTINGKIT = "PYACCOUNTINGKIT"


class ReadBackend(StrEnum):
    """Primary backend for a CFA FRA read operation."""

    LEGACY = "LEGACY"
    PYACCOUNTINGKIT = "PYACCOUNTINGKIT"


@dataclass(frozen=True, slots=True)
class MigrationRouting:
    """Per-operation strangler routing.

    Unspecified operations remain on the legacy backend. This fail-safe default
    prevents an accidental migration merely by installing the compatibility layer.
    """

    mutation_routes: Mapping[str, MutationBackend] = field(default_factory=dict)
    read_routes: Mapping[str, ReadBackend] = field(default_factory=dict)
    dual_run_reads: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mutation_routes",
            MappingProxyType(dict(self.mutation_routes)),
        )
        object.__setattr__(
            self,
            "read_routes",
            MappingProxyType(dict(self.read_routes)),
        )
        object.__setattr__(self, "dual_run_reads", frozenset(self.dual_run_reads))

    def mutation_backend_for(self, operation: str) -> MutationBackend:
        return self.mutation_routes.get(operation, MutationBackend.LEGACY)

    def read_backend_for(self, operation: str) -> ReadBackend:
        return self.read_routes.get(operation, ReadBackend.LEGACY)


@dataclass(frozen=True, slots=True)
class DualRunObservation:
    """One read-side shadow comparison without retaining consumer payloads."""

    operation: str
    primary_backend: ReadBackend
    matched: bool


@dataclass(frozen=True, slots=True)
class LegacyIdentityLink:
    """Trace one historical CFA FRA identity into a PyAccountingKit identity."""

    legacy_type: str
    legacy_id: str
    target_type: str
    target_id: str
    source: str = "CFA_FRA_LEGACY"
    source_checksum: str | None = None

    def __post_init__(self) -> None:
        for value in (
            self.legacy_type,
            self.legacy_id,
            self.target_type,
            self.target_id,
            self.source,
        ):
            if not value.strip():
                raise ValueError("legacy identity fields must not be empty")


class LegacyIdentityMap:
    """In-memory migration artifact preserving historical identity traceability."""

    def __init__(self, links: tuple[LegacyIdentityLink, ...] = ()) -> None:
        self._links: dict[tuple[str, str], LegacyIdentityLink] = {}
        for link in links:
            self.register(link)

    def register(self, link: LegacyIdentityLink) -> LegacyIdentityLink:
        key = (link.legacy_type, link.legacy_id)
        existing = self._links.get(key)
        if existing is not None and existing != link:
            raise CFAFRAMigrationRouteError(
                "legacy identity already maps to a different target: "
                f"{link.legacy_type}:{link.legacy_id}"
            )
        self._links[key] = link
        return link

    def resolve(self, legacy_type: str, legacy_id: str) -> LegacyIdentityLink | None:
        return self._links.get((legacy_type, legacy_id))

    def snapshot(self) -> tuple[LegacyIdentityLink, ...]:
        return tuple(self._links[key] for key in sorted(self._links))


ContextFactory = Callable[[object], CommandContext]
DualRunComparator = Callable[[object, object], bool]
ObservationSink = Callable[[DualRunObservation], None]
TargetCall = Callable[[CommandContext], object]
LegacyCall = Callable[..., object]


def _default_comparator(legacy: object, target: object) -> bool:
    return legacy == target


def _ignore_observation(observation: DualRunObservation) -> None:
    del observation


class CFAFRACompatibilityAdapter:
    """Temporary old-signature facade delegating CFA FRA into AccountingApplication."""

    __slots__ = (
        "_application",
        "_legacy_service",
        "_routing",
        "_context_factory",
        "_comparator",
        "_observation_sink",
        "identities",
    )

    def __init__(
        self,
        application: AccountingApplication,
        *,
        legacy_service: object | None,
        routing: MigrationRouting,
        context_factory: ContextFactory,
        comparator: DualRunComparator = _default_comparator,
        observation_sink: ObservationSink = _ignore_observation,
        identities: LegacyIdentityMap | None = None,
    ) -> None:
        self._application = application
        self._legacy_service = legacy_service
        self._routing = routing
        self._context_factory = context_factory
        self._comparator = comparator
        self._observation_sink = observation_sink
        self.identities = identities if identities is not None else LegacyIdentityMap()

    def post_entry(
        self,
        *,
        entry_id: object,
        user: object,
        **parameters: object,
    ) -> object:
        """Migrate posting with an exclusive mutation feature switch."""
        legacy_parameters = {"entry_id": entry_id, "user": user, **parameters}
        return self._mutation(
            "post_entry",
            user,
            legacy_parameters,
            lambda context: self._application.entries.post(
                entry_id=entry_id,
                context=context,
                **parameters,
            ),
        )

    def reverse_entry(
        self,
        *,
        entry_id: object,
        user: object,
        **parameters: object,
    ) -> object:
        """Migrate reversal without ever dual-writing."""
        legacy_parameters = {"entry_id": entry_id, "user": user, **parameters}
        return self._mutation(
            "reverse_entry",
            user,
            legacy_parameters,
            lambda context: self._application.entries.reverse(
                entry_id=entry_id,
                context=context,
                **parameters,
            ),
        )

    def execute_fec_import(
        self,
        *,
        import_id: object,
        user: object,
        **parameters: object,
    ) -> object:
        """Migrate FEC execution through the public imports namespace."""
        legacy_parameters = {"import_id": import_id, "user": user, **parameters}
        return self._mutation(
            "execute_fec_import",
            user,
            legacy_parameters,
            lambda context: self._application.imports.execute(
                import_id=import_id,
                context=context,
                **parameters,
            ),
        )

    def close_period(
        self,
        *,
        period_id: object,
        user: object,
        **parameters: object,
    ) -> object:
        """Migrate closing using one mutation backend only."""
        legacy_parameters = {"period_id": period_id, "user": user, **parameters}
        return self._mutation(
            "close_period",
            user,
            legacy_parameters,
            lambda context: self._application.closing.close(
                period_id=period_id,
                context=context,
                **parameters,
            ),
        )

    def trial_balance(
        self,
        *,
        period_id: object,
        user: object,
        **parameters: object,
    ) -> object:
        """Read trial balance from the configured primary and optional shadow backend."""
        legacy_parameters = {"period_id": period_id, "user": user, **parameters}
        return self._read(
            "trial_balance",
            user,
            legacy_parameters,
            lambda context: self._application.ledger.trial_balance(
                period_id=period_id,
                context=context,
                **parameters,
            ),
        )

    def financial_statements(
        self,
        *,
        period_id: object,
        user: object,
        **parameters: object,
    ) -> object:
        """Read financial statements through the strangler route."""
        legacy_parameters = {"period_id": period_id, "user": user, **parameters}
        return self._read(
            "financial_statements",
            user,
            legacy_parameters,
            lambda context: self._application.statements.build(
                period_id=period_id,
                context=context,
                **parameters,
            ),
        )

    def run_controls(
        self,
        *,
        period_id: object,
        user: object,
        **parameters: object,
    ) -> object:
        """Read control results through the configured route."""
        legacy_parameters = {"period_id": period_id, "user": user, **parameters}
        return self._read(
            "run_controls",
            user,
            legacy_parameters,
            lambda context: self._application.controls.run(
                period_id=period_id,
                context=context,
                **parameters,
            ),
        )

    def effective_plan(
        self,
        *,
        user: object,
        **parameters: object,
    ) -> object:
        """Replace local regulatory authority with provider-backed public references."""
        legacy_parameters = {"user": user, **parameters}
        return self._read(
            "effective_plan",
            user,
            legacy_parameters,
            lambda context: self._application.references.get_effective_plan(
                context=context,
                **parameters,
            ),
        )

    def _mutation(
        self,
        operation: str,
        user: object,
        legacy_parameters: Mapping[str, object],
        target_call: TargetCall,
    ) -> object:
        backend = self._routing.mutation_backend_for(operation)
        if backend is MutationBackend.LEGACY:
            return self._legacy_call(operation, legacy_parameters)
        context = self._context_factory(user)
        return target_call(context)

    def _read(
        self,
        operation: str,
        user: object,
        legacy_parameters: Mapping[str, object],
        target_call: TargetCall,
    ) -> object:
        backend = self._routing.read_backend_for(operation)
        if operation not in self._routing.dual_run_reads:
            if backend is ReadBackend.LEGACY:
                return self._legacy_call(operation, legacy_parameters)
            return target_call(self._context_factory(user))

        legacy_result = self._legacy_call(operation, legacy_parameters)
        target_result = target_call(self._context_factory(user))
        self._observation_sink(
            DualRunObservation(
                operation=operation,
                primary_backend=backend,
                matched=self._comparator(legacy_result, target_result),
            )
        )
        if backend is ReadBackend.LEGACY:
            return legacy_result
        return target_result

    def _legacy_call(
        self,
        operation: str,
        parameters: Mapping[str, object],
    ) -> object:
        if self._legacy_service is None:
            raise CFAFRAMigrationRouteError(
                f"legacy backend unavailable for CFA FRA operation {operation!r}"
            )
        candidate = getattr(self._legacy_service, operation, None)
        if not callable(candidate):
            raise CFAFRAMigrationRouteError(f"legacy operation {operation!r} is unavailable")
        call = cast(LegacyCall, candidate)
        return call(**dict(parameters))


__all__ = [
    "CFAFRACompatibilityAdapter",
    "CFAFRAMigrationRouteError",
    "DualRunObservation",
    "LegacyIdentityLink",
    "LegacyIdentityMap",
    "MigrationRouting",
    "MutationBackend",
    "ReadBackend",
]
