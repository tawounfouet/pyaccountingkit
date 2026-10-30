"""L05-03: scoped, read-only proposal preview; not an IAM/C10 boundary."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from ..domain.chart_of_accounts.versions_bindings import (
    BookChartBindingCandidate,
    BookChartCandidateReadReceipt,
    BookChartPurpose,
    CompanyChartVersionCandidate,
    InvalidBookChartBinding,
    preview_book_chart_candidate,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from .ports import AuthorizationPort, TrustedPrincipal


class ChartCandidateVersionsReader(Protocol):
    def list_for_book_scope(
        self, scope: ConfigurationScope
    ) -> tuple[CompanyChartVersionCandidate, ...]: ...


class BookChartBindingsReader(Protocol):
    def list_for_book(
        self, scope: ConfigurationScope
    ) -> tuple[BookChartBindingCandidate, ...]: ...


@dataclass(frozen=True, slots=True)
class PreviewBookChartCandidate:
    scope: ConfigurationScope
    purpose: BookChartPurpose
    as_of: date
    known_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is None:
            raise InvalidBookChartBinding("Book-level scope required")
        if not isinstance(self.purpose, BookChartPurpose) or type(self.as_of) is not date:
            raise InvalidBookChartBinding("Purpose and business date required")
        if (
            type(self.known_at) is not datetime
            or self.known_at.tzinfo is None
            or self.known_at.utcoffset() is None
        ):
            raise InvalidBookChartBinding("Aware known_at required")


class BookChartCandidatePreviewService:
    """A fake-grant-protected read; real book membership remains unverified."""

    def __init__(
        self,
        *, versions: ChartCandidateVersionsReader,
        bindings: BookChartBindingsReader,
        authorization: AuthorizationPort,
    ) -> None:
        self._versions = versions
        self._bindings = bindings
        self._authorization = authorization

    def preview(
        self, query: PreviewBookChartCandidate, *, principal: TrustedPrincipal
    ) -> BookChartCandidateReadReceipt:
        if not isinstance(query, PreviewBookChartCandidate):
            raise TypeError("Typed book chart preview query required")
        if not isinstance(principal, TrustedPrincipal):
            raise PermissionError("Unverified chart preview principal")
        if principal.tenant_id != query.scope.tenant_id:
            raise PermissionError("Cross-tenant chart preview denied")
        self._authorization.require(
            principal=principal, action="chart.binding.candidate.preview",
            scope=query.scope,
        )
        return preview_book_chart_candidate(
            book_scope=query.scope, purpose=query.purpose,
            as_of=query.as_of, known_at=query.known_at,
            bindings=self._bindings.list_for_book(query.scope),
            chart_versions=self._versions.list_for_book_scope(query.scope),
        )
