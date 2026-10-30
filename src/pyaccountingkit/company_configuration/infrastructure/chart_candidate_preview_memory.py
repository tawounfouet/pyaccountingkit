"""L05-03 read-only process fixtures, never authoritative chart persistence."""

from ..domain.chart_of_accounts.versions_bindings import (
    BookChartBindingCandidate,
    CompanyChartVersionCandidate,
    InvalidBookChartBinding,
    InvalidChartCandidateVersion,
)
from ..domain.shared.accounting_scope import ConfigurationScope


class MemoryChartCandidateVersions:
    def __init__(self, versions: tuple[CompanyChartVersionCandidate, ...]) -> None:
        if not isinstance(versions, tuple) or any(
            not isinstance(v, CompanyChartVersionCandidate) for v in versions
        ):
            raise InvalidChartCandidateVersion("Typed immutable chart version tuple required")
        self._versions = versions

    def list_for_book_scope(
        self, scope: ConfigurationScope
    ) -> tuple[CompanyChartVersionCandidate, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is None:
            raise InvalidChartCandidateVersion("Book-level query scope required")
        return tuple(
            v for v in self._versions
            if (
                v.chart.scope.tenant_id == scope.tenant_id
                and v.chart.scope.company_id == scope.company_id
                and v.chart.scope.legal_entity_id == scope.legal_entity_id
            )
        )


class MemoryBookChartBindings:
    def __init__(self, bindings: tuple[BookChartBindingCandidate, ...]) -> None:
        if not isinstance(bindings, tuple) or any(
            not isinstance(v, BookChartBindingCandidate) for v in bindings
        ):
            raise InvalidBookChartBinding("Typed immutable binding tuple required")
        self._bindings = bindings

    def list_for_book(
        self, scope: ConfigurationScope
    ) -> tuple[BookChartBindingCandidate, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is None:
            raise InvalidBookChartBinding("Book-level query scope required")
        return tuple(b for b in self._bindings if b.book_scope == scope)
