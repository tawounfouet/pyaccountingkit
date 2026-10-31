"""L05-05: read-only, fake-gated conditional resolution and coverage queries."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from ..domain.chart_of_accounts.mapping import InvalidMappingCandidate
from ..domain.chart_of_accounts.mapping_conditions import (
    ConditionalMappingCandidateResolution,
    MappingConditionProfileCandidate,
    MappingFact,
    resolve_conditional_mapping_candidate,
)
from ..domain.chart_of_accounts.mapping_coverage import (
    MappingCoverageCandidateReport,
    MappingCoverageExceptionCandidate,
    preview_mapping_coverage_candidate,
)
from ..domain.chart_of_accounts.mapping_provider import MappingProviderRequirementCandidate
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.identifiers import CompanyAccountId
from .ports import AuthorizationPort, TrustedPrincipal


class MappingDiagnosticsCandidateReader(Protocol):
    """An untrusted read-only test port, NOT the published C10 provider."""

    def profiles_for_scope(
        self, scope: ConfigurationScope
    ) -> tuple[MappingConditionProfileCandidate, ...]: ...

    def providers_for_scope(
        self, scope: ConfigurationScope
    ) -> tuple[MappingProviderRequirementCandidate, ...]: ...

    def exceptions_for_scope(
        self, scope: ConfigurationScope
    ) -> tuple[MappingCoverageExceptionCandidate, ...]: ...


@dataclass(frozen=True, slots=True)
class MappingDiagnosticsCandidateQuery:
    scope: ConfigurationScope
    mapping_set_version_id: object
    as_of: date
    known_at: datetime

    def __post_init__(self) -> None:
        from ..domain.shared.identifiers import MappingSetCandidateVersionId

        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidMappingCandidate("Entity-level diagnostics scope required")
        if not isinstance(self.mapping_set_version_id, MappingSetCandidateVersionId):
            raise InvalidMappingCandidate("Exact typed mapping-set version ID required")
        if type(self.as_of) is not date or type(self.known_at) is not datetime or (
            self.known_at.tzinfo is None or self.known_at.utcoffset() is None
        ):
            raise InvalidMappingCandidate("Business date and aware known-at required")


class MappingDiagnosticsCandidateService:
    def __init__(
        self, *, reader: MappingDiagnosticsCandidateReader,
        authorization: AuthorizationPort,
    ) -> None:
        self._reader = reader
        self._authorization = authorization

    def _profile(
        self, query: MappingDiagnosticsCandidateQuery, principal: TrustedPrincipal,
        action: str,
    ) -> MappingConditionProfileCandidate:
        if not isinstance(query, MappingDiagnosticsCandidateQuery):
            raise TypeError("Typed query required")
        if not isinstance(principal, TrustedPrincipal):
            raise PermissionError("Unverified candidate diagnostics actor")
        if principal.tenant_id != query.scope.tenant_id:
            raise PermissionError("Cross-tenant diagnostics read denied")
        self._authorization.require(
            principal=principal, action=action, scope=query.scope
        )
        items = self._reader.profiles_for_scope(query.scope)
        if not isinstance(items, tuple):
            raise InvalidMappingCandidate("Immutable condition profiles required")
        seen: set[object] = set()
        matches = []
        for profile in items:
            if not isinstance(profile, MappingConditionProfileCandidate):
                raise InvalidMappingCandidate("Non-typed conditional profile")
            if profile.mapping_set.scope != query.scope:
                raise InvalidMappingCandidate("Leaked foreign mapping-set profile")
            profile.verify_integrity()
            identifier = profile.mapping_set.id
            if identifier in seen:
                raise InvalidMappingCandidate("Duplicate mapping-set profile identity")
            seen.add(identifier)
            if identifier == query.mapping_set_version_id:
                matches.append(profile)
        if len(matches) != 1:
            raise InvalidMappingCandidate("Exact condition profile missing or ambiguous")
        return matches[0]

    def resolve(
        self, query: MappingDiagnosticsCandidateQuery, *,
        principal: TrustedPrincipal, source_account_id: CompanyAccountId,
        facts: tuple[MappingFact, ...],
    ) -> ConditionalMappingCandidateResolution:
        profile = self._profile(
            query, principal, "chart.mapping.condition.candidate.preview"
        )
        return resolve_conditional_mapping_candidate(
            profile=profile, source_account_id=source_account_id, facts=facts,
            as_of=query.as_of, known_at=query.known_at,
        )

    def coverage(
        self, query: MappingDiagnosticsCandidateQuery, *,
        principal: TrustedPrincipal,
    ) -> MappingCoverageCandidateReport:
        profile = self._profile(
            query, principal, "chart.mapping.coverage.candidate.preview"
        )
        providers = self._reader.providers_for_scope(query.scope)
        exceptions = self._reader.exceptions_for_scope(query.scope)
        return preview_mapping_coverage_candidate(
            mapping_set=profile.mapping_set, as_of=query.as_of, known_at=query.known_at,
            conditions=profile, providers=providers, exceptions=exceptions,
        )
