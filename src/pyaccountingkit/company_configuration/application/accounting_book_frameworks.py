"""L04-04: read-only framework binding preview orchestrating R&D ports.

The Normative Layer check is a mandatory protocol; the memory adapter below
is only a test fake. This is NOT C10 or production configuration resolution.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from typing import Protocol

from ..domain.accounting_books import (
    BookAssignmentMissing,
    BookAssignmentPurpose,
    BookFrameworkPreview,
    ReferenceFrameworkBindingCandidate,
    InvalidFrameworkBinding,
    preview_applicable_book_drafts,
    preview_reference_framework_binding,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.references import ReferenceFrameworkRef
from .accounting_book_assignments import BookAssignmentCandidateReader
from .accounting_books import (
    BookDraftAuthorization,
    BookDraftNotFound,
    BookDraftPermissionDenied,
    BookDraftUnitOfWork,
    CompanyEntityMembership,
)
from .ports import TrustedPrincipal


@dataclass(frozen=True, slots=True)
class PreviewBookFrameworkBinding:
    scope: ConfigurationScope
    purpose: BookAssignmentPurpose
    as_of: date

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is None:
            raise InvalidFrameworkBinding("Book-level scope required")
        if not isinstance(self.purpose, BookAssignmentPurpose):
            raise InvalidFrameworkBinding("Typed purpose required")
        if type(self.as_of) is not date:
            raise InvalidFrameworkBinding("A business date (not datetime) is required")


class BookFrameworkCandidateReader(Protocol):
    def list_for_book(
        self, scope: ConfigurationScope
    ) -> tuple[ReferenceFrameworkBindingCandidate, ...]: ...


class NormativeFrameworkAvailability(Protocol):
    """Normative authority contract, not provided by PyAccountingKit R&D fakes."""

    def require_available(
        self, framework: ReferenceFrameworkRef, *, as_of: date
    ) -> None: ...


class BookFrameworkPreviewService:
    """Only a test-local, read-only composition; never a posting authorization."""

    def __init__(
        self,
        uow_factory: Callable[[], BookDraftUnitOfWork],
        assignments: BookAssignmentCandidateReader,
        frameworks: BookFrameworkCandidateReader,
        authorization: BookDraftAuthorization,
        membership: CompanyEntityMembership,
        normative: NormativeFrameworkAvailability,
    ) -> None:
        self._uow_factory = uow_factory
        self._assignments = assignments
        self._frameworks = frameworks
        self._authorization = authorization
        self._membership = membership
        self._normative = normative

    def preview(
        self, query: PreviewBookFrameworkBinding, *, principal: TrustedPrincipal
    ) -> BookFrameworkPreview:
        if not isinstance(query, PreviewBookFrameworkBinding):
            raise TypeError("Expected PreviewBookFrameworkBinding")
        if not isinstance(principal, TrustedPrincipal):
            raise BookDraftPermissionDenied("Verified principal required")
        if principal.tenant_id != query.scope.tenant_id:
            raise BookDraftPermissionDenied("Cross-tenant framework preview denied")
        self._authorization.require(
            principal=principal, action="book.framework.preview", scope=query.scope
        )
        self._membership.require(scope=query.scope)

        with self._uow_factory() as uow:
            book = uow.books.get(query.scope)
            if book is None:
                raise BookDraftNotFound("Requested draft book unavailable within scope")
            entity_scope = replace(query.scope, book_id=None)
            eligible = preview_applicable_book_drafts(
                scope=entity_scope,
                purpose=query.purpose,
                as_of=query.as_of,
                books=uow.books.list_for_entity(entity_scope),
                assignments=self._assignments.list_for_entity(entity_scope),
            )
            if not any(candidate.id == book.id for candidate in eligible):
                raise BookAssignmentMissing("Requested book has no assignment for purpose/date")

            selected = preview_reference_framework_binding(
                book=book,
                scope=query.scope,
                purpose=query.purpose,
                as_of=query.as_of,
                bindings=self._frameworks.list_for_book(query.scope),
            )
            # Real normative reference availability is REQUIRED by contract,
            # but a local fake cannot prove applicability in any jurisdiction.
            self._normative.require_available(selected.framework, as_of=query.as_of)
            return selected
