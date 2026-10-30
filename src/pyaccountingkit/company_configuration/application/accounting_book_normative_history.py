"""L04-05: query facade for *normative claims history* on current book drafts.

Only normative declarations use known_at here. Draft books/assignments/bindings
are not historized or published: this is NOT full bitemporal C10 resolution.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Protocol

from ..domain.accounting_books import (
    BookAssignmentMissing,
    BookAssignmentPurpose,
    BookFrameworkPreview,
    InvalidNormativeStatement,
    NormativeReferenceHistoricalPreview,
    NormativeReferenceStatement,
    NormativeSourceCode,
    preview_applicable_book_drafts,
    preview_normative_reference_history,
    preview_reference_framework_binding,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.references import ReferenceFrameworkRef
from .accounting_book_assignments import BookAssignmentCandidateReader
from .accounting_book_frameworks import BookFrameworkCandidateReader
from .accounting_books import (
    BookDraftAuthorization,
    BookDraftNotFound,
    BookDraftPermissionDenied,
    BookDraftUnitOfWork,
    CompanyEntityMembership,
)
from .ports import TrustedPrincipal


@dataclass(frozen=True, slots=True)
class PreviewNormativeHistoryForBookDraft:
    scope: ConfigurationScope
    purpose: BookAssignmentPurpose
    source: NormativeSourceCode
    as_of: date
    known_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is None:
            raise InvalidNormativeStatement("Book-level scope required")
        if not isinstance(self.purpose, BookAssignmentPurpose):
            raise InvalidNormativeStatement("Typed assignment purpose required")
        if not isinstance(self.source, NormativeSourceCode):
            raise InvalidNormativeStatement("Typed external source required")
        if type(self.as_of) is not date:
            raise InvalidNormativeStatement("Business date required")
        if (
            type(self.known_at) is not datetime
            or self.known_at.tzinfo is None
            or self.known_at.utcoffset() is None
        ):
            raise InvalidNormativeStatement("Timezone-aware known_at required")


@dataclass(frozen=True, slots=True)
class BookNormativeHistoryPreview:
    book_binding: BookFrameworkPreview
    normative_claim: NormativeReferenceHistoricalPreview


class NormativeReferenceClaimsReader(Protocol):
    """Test/read model port; this is NOT a certified Normative Registry adapter."""

    def list_for_reference(
        self, framework: ReferenceFrameworkRef, source: NormativeSourceCode
    ) -> tuple[NormativeReferenceStatement, ...]: ...


class BookNormativeHistoryPreviewService:
    """Read-only composition of CURRENT draft + HISTORICAL normative claims."""

    def __init__(
        self,
        uow_factory: Callable[[], BookDraftUnitOfWork],
        assignments: BookAssignmentCandidateReader,
        frameworks: BookFrameworkCandidateReader,
        statements: NormativeReferenceClaimsReader,
        authorization: BookDraftAuthorization,
        membership: CompanyEntityMembership,
    ) -> None:
        self._uow_factory = uow_factory
        self._assignments = assignments
        self._frameworks = frameworks
        self._statements = statements
        self._authorization = authorization
        self._membership = membership

    def preview(
        self, query: PreviewNormativeHistoryForBookDraft, *,
        principal: TrustedPrincipal,
    ) -> BookNormativeHistoryPreview:
        if not isinstance(query, PreviewNormativeHistoryForBookDraft):
            raise TypeError("Expected PreviewNormativeHistoryForBookDraft")
        if not isinstance(principal, TrustedPrincipal):
            raise BookDraftPermissionDenied("Verified principal required")
        if principal.tenant_id != query.scope.tenant_id:
            raise BookDraftPermissionDenied("Cross-tenant normative preview denied")

        self._authorization.require(
            principal=principal, action="book.normative_history.preview",
            scope=query.scope,
        )
        self._membership.require(scope=query.scope)

        with self._uow_factory() as uow:
            current = uow.books.get(query.scope)
            if current is None:
                raise BookDraftNotFound("Draft book not found within scope")
            entity_scope = replace(query.scope, book_id=None)
            eligible = preview_applicable_book_drafts(
                scope=entity_scope,
                purpose=query.purpose,
                as_of=query.as_of,
                books=uow.books.list_for_entity(entity_scope),
                assignments=self._assignments.list_for_entity(entity_scope),
            )
            if not any(x.id == current.id for x in eligible):
                raise BookAssignmentMissing("Book is not assigned for purpose/date")
            binding = preview_reference_framework_binding(
                book=current, scope=query.scope, purpose=query.purpose,
                as_of=query.as_of,
                bindings=self._frameworks.list_for_book(query.scope),
            )
            claim = preview_normative_reference_history(
                framework=binding.framework,
                source=query.source,
                as_of=query.as_of,
                known_at=query.known_at,
                statements=self._statements.list_for_reference(
                    binding.framework, query.source
                ),
            )
            return BookNormativeHistoryPreview(
                book_binding=binding, normative_claim=claim
            )
