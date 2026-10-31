"""L05-05 immutable scoped read fixture; not an authoritative registry."""

from ..domain.chart_of_accounts.mapping import InvalidMappingCandidate
from ..domain.chart_of_accounts.mapping_conditions import MappingConditionProfileCandidate
from ..domain.chart_of_accounts.mapping_coverage import MappingCoverageExceptionCandidate
from ..domain.chart_of_accounts.mapping_provider import MappingProviderRequirementCandidate
from ..domain.shared.accounting_scope import ConfigurationScope


class MemoryMappingDiagnosticsCandidates:
    def __init__(
        self, *,
        profiles: tuple[MappingConditionProfileCandidate, ...],
        providers: tuple[MappingProviderRequirementCandidate, ...] = (),
        exceptions: tuple[MappingCoverageExceptionCandidate, ...] = (),
    ) -> None:
        for value, kind in (
            (profiles, MappingConditionProfileCandidate),
            (providers, MappingProviderRequirementCandidate),
            (exceptions, MappingCoverageExceptionCandidate),
        ):
            if not isinstance(value, tuple) or any(
                not isinstance(item, kind) for item in value
            ):
                raise InvalidMappingCandidate("Typed immutable diagnostics catalogs required")
        self._profiles = profiles
        self._providers = providers
        self._exceptions = exceptions

    def profiles_for_scope(
        self, scope: ConfigurationScope
    ) -> tuple[MappingConditionProfileCandidate, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
            raise InvalidMappingCandidate("Entity-level query scope required")
        return tuple(p for p in self._profiles if p.mapping_set.scope == scope)

    def providers_for_scope(
        self, scope: ConfigurationScope
    ) -> tuple[MappingProviderRequirementCandidate, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
            raise InvalidMappingCandidate("Entity-level query scope required")
        return tuple(p for p in self._providers if p.mapping_set.scope == scope)

    def exceptions_for_scope(
        self, scope: ConfigurationScope
    ) -> tuple[MappingCoverageExceptionCandidate, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
            raise InvalidMappingCandidate("Entity-level query scope required")
        return tuple(
            p for p in self._exceptions
            if any(
                q.mapping_set.id == p.mapping_set_version_id
                and q.mapping_set.scope == scope
                for q in self._profiles
            )
        )
