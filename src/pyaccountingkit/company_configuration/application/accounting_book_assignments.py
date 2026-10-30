"""L04-03: read-only preview of candidate book assignments.

Not C10, not published data, not authorization to post or validate ownership.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ..domain.accounting_books import (
    BookAssignmentCandidate,
    BookAssignmentPurpose,
    InvalidBookAssignment,
    preview_applicable_book_drafts,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from .accounting_books import (
    BookDraftAuthorization,
    BookDraftPermissionDenied,
    BookDraftUnitOfWork,
    CompanyEntityMembership,
)
from .ports import TrustedPrincipal


def _entity_scope(scope: ConfigurationScope) -> None:
    if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
        raise InvalidBookAssignment("An entity-level scope without book_id is required")


@dataclass(frozen=True, slots=True)
class ListBookAssignmentCandidates:
    scope: ConfigurationScope

    def __post_init__(self) -> None:
        _entity_scope(self.scope)


@dataclass(frozen=True, slots=True)
class PreviewAssignedBookDrafts:
    scope: ConfigurationScope
    purpose: BookAssignmentPurpose
    as_of: date

    def __post_init__(self) -> None:
        _entity_scope(self.scope)
        if not isinstance(self.purpose, BookAssignmentPurpose):
            raise InvalidBookAssignment("Typed purpose required")
        if type(self.as_of) is not date:
            raise InvalidBookAssignment("Business date required; datetime is not accepted")


class BookAssignmentCandidateReader(Protocol):
    """Read-only candidate data; no mutation or authoritative ownership."""

    def list_for_entity(
        self, scope: ConfigurationScope
    ) -> tuple[BookAssignmentCandidate, ...]: ...


class BookAssignmentPreviewService:
    """Fail-closed in-memory R&D query facade; no publication or C10 contract."""

    def __init__(
        self,
        uow_factory: Callable[[], BookDraftUnitOfWork],
        assignments: BookAssignmentCandidateReader,
        authorization: BookDraftAuthorization,
        membership: CompanyEntityMembership,
    ) -> None:
        self._uow_factory = uow_factory
        self._assignments = assignments
        self._authorization = authorization
        self._membership = membership

    def _check(self, principal: TrustedPrincipal, scope: ConfigurationScope) -> None:
        if not isinstance(principal, TrustedPrincipal):
            raise BookDraftPermissionDenied("Verified principal required")
        if principal.tenant_id != scope.tenant_id:
            raise BookDraftPermissionDenied("Cross-tenant preview forbidden")
        self._authorization.require(
            principal=principal, action="book.assignment.preview", scope=scope
        )
        self._membership.require(scope=scope)

    def list_candidates(
        self, query: ListBookAssignmentCandidates, *, principal: TrustedPrincipal
    ) -> tuple[BookAssignmentCandidate, ...]:
        if not isinstance(query, ListBookAssignmentCandidates):
            raise TypeError("Expected ListBookAssignmentCandidates")
        self._check(principal, query.scope)
        candidates = self._assignments.list_for_entity(query.scope)
        if not isinstance(candidates, tuple):
            raise InvalidBookAssignment("Candidate reader must return an immutable tuple")
        for candidate in candidates:
            if not isinstance(candidate, BookAssignmentCandidate) or (
                candidate.scope.tenant_id != query.scope.tenant_id
                or candidate.scope.company_id != query.scope.company_id
                or candidate.scope.legal_entity_id != query.scope.legal_entity_id
            ):
                raise InvalidBookAssignment("Candidate reader returned out-of-scope value")
        return tuple(sorted(candidates, key=lambda x: (str(x.scope.book_id), str(x.id))))

    def preview(
        self, query: PreviewAssignedBookDrafts, *, principal: TrustedPrincipal
    ):
        if not isinstance(query, PreviewAssignedBookDrafts):
            raise TypeError("Expected PreviewAssignedBookDrafts")
        self._check(principal, query.scope)
        with self._uow_factory() as uow:
            books = uow.books.list_for_entity(query.scope)
            candidates = self._assignments.list_for_entity(query.scope)
            return preview_applicable_book_drafts(
                scope=query.scope,
                purpose=query.purpose,
                as_of=query.as_of,
                books=books,
                assignments=candidates,
            )
