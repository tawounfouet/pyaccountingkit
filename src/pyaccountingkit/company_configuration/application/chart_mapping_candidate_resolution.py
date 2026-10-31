"""L05-04 read-only candidate mapping resolver; no published C10 or Ledger."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from ..domain.chart_of_accounts.mapping import (
    AccountMappingCandidateResolution,
    InvalidMappingCandidate,
    MappingSetVersionCandidate,
    resolve_account_mapping_candidate,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.identifiers import CompanyAccountId
from .ports import AuthorizationPort, TrustedPrincipal


class MappingSetCandidateReader(Protocol):
    def list_for_scope(
        self, scope: ConfigurationScope
    ) -> tuple[MappingSetVersionCandidate, ...]: ...


@dataclass(frozen=True, slots=True)
class ResolveAccountMappingCandidate:
    scope: ConfigurationScope
    source_account_id: CompanyAccountId
    as_of: date
    known_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidMappingCandidate("Entity-level mapping scope required")
        if not isinstance(self.source_account_id, CompanyAccountId) or type(self.as_of) is not date:
            raise InvalidMappingCandidate("Typed source account and business date required")
        if type(self.known_at) is not datetime or self.known_at.tzinfo is None or (
            self.known_at.utcoffset() is None
        ):
            raise InvalidMappingCandidate("Aware known_at required")


class AccountMappingCandidateResolutionService:
    """Fake-gated R&D read port; TrustedPrincipal is NOT live IAM authority."""

    def __init__(
        self, *, sets: MappingSetCandidateReader, authorization: AuthorizationPort
    ) -> None:
        self._sets = sets
        self._authorization = authorization

    def resolve(
        self, query: ResolveAccountMappingCandidate, *, principal: TrustedPrincipal
    ) -> AccountMappingCandidateResolution:
        if not isinstance(query, ResolveAccountMappingCandidate):
            raise TypeError("Typed mapping candidate query required")
        if not isinstance(principal, TrustedPrincipal):
            raise PermissionError("Unverified mapping preview principal")
        if principal.tenant_id != query.scope.tenant_id:
            raise PermissionError("Cross-tenant mapping preview denied")
        self._authorization.require(
            principal=principal,
            action="chart.mapping.candidate.resolve",
            scope=query.scope,
        )
        return resolve_account_mapping_candidate(
            scope=query.scope,
            source_account_id=query.source_account_id,
            as_of=query.as_of,
            known_at=query.known_at,
            mapping_sets=self._sets.list_for_scope(query.scope),
        )
