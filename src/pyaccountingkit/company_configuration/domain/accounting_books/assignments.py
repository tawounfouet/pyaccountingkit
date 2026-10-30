"""L04-03: candidate BookAssignment value model and pure, non-postable preview.

BOOK-ADR-01 remains PROPOSED: entity-scoped use is a temporary R&D guard;
representation of an assignment must not confer ownership or posting rights.
"""

import re
from dataclasses import dataclass
from datetime import date

from ..shared.accounting_scope import ConfigurationScope
from ..shared.effective_interval import EffectiveInterval
from ..shared.errors import DomainError
from ..shared.identifiers import BookAssignmentId
from .model import AccountingBookDraft


class InvalidBookAssignment(DomainError):
    code = "INVALID_BOOK_ASSIGNMENT"


class BookAssignmentMissing(DomainError):
    code = "BOOK_ASSIGNMENT_MISSING"


class BookAssignmentAmbiguous(DomainError):
    code = "BOOK_ASSIGNMENT_AMBIGUOUS"


@dataclass(frozen=True, slots=True)
class BookAssignmentPurpose:
    """Provisional explicit usage code, not a normative BookKind taxonomy."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not re.fullmatch(
            r"[A-Z][A-Z0-9_]{0,31}", self.value
        ):
            raise InvalidBookAssignment("Assignment purpose must be canonical uppercase ASCII")


@dataclass(frozen=True, slots=True)
class BookAssignmentCandidate:
    """A proposed, dated BookId-to-entity link, never a published authorization."""

    id: BookAssignmentId
    scope: ConfigurationScope
    purpose: BookAssignmentPurpose
    effective: EffectiveInterval
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, BookAssignmentId):
            raise InvalidBookAssignment("Typed BookAssignmentId required")
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is None:
            raise InvalidBookAssignment("Book-level ConfigurationScope required")
        if not isinstance(self.purpose, BookAssignmentPurpose):
            raise InvalidBookAssignment("Typed BookAssignmentPurpose required")
        if not isinstance(self.effective, EffectiveInterval):
            raise InvalidBookAssignment("Explicit effective interval required")
        if (
            not isinstance(self.source_ref, str)
            or not self.source_ref.strip()
            or self.source_ref.strip() != self.source_ref
        ):
            raise InvalidBookAssignment("Nonblank trimmed provenance pointer required")

    def require_candidate_compatibility(self, book: AccountingBookDraft) -> None:
        """Temporary mono-entity *preview* boundary; not permanent ownership."""
        if not isinstance(book, AccountingBookDraft):
            raise InvalidBookAssignment("An AccountingBookDraft is required")
        if self.scope != book.scope:
            raise InvalidBookAssignment("Cross-entity/company/tenant book assignment denied")
        if self.effective.start < book.effective.start or (
            book.effective.end is not None
            and (self.effective.end is None or self.effective.end > book.effective.end)
        ):
            raise InvalidBookAssignment("Assignment extends beyond book effective interval")


def preview_applicable_book_drafts(
    *,
    scope: ConfigurationScope,
    purpose: BookAssignmentPurpose,
    as_of: date,
    books: tuple[AccountingBookDraft, ...],
    assignments: tuple[BookAssignmentCandidate, ...],
) -> tuple[AccountingBookDraft, ...]:
    """Fail-closed preview only, NOT C10 GetApplicableBooks or permission to post.

    Reject foreign/unknown references and overlapping assignments instead of
    assuming the first or most recently written candidate is applicable.
    """
    if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
        raise InvalidBookAssignment("An explicit entity-level scope is required")
    if not isinstance(purpose, BookAssignmentPurpose):
        raise InvalidBookAssignment("A typed purpose is required")
    if type(as_of) is not date:
        raise InvalidBookAssignment("as_of must be a business date")
    if not isinstance(books, tuple) or not isinstance(assignments, tuple):
        raise InvalidBookAssignment("Candidate collections must be immutable tuples")
    by_id = {}
    for book in books:
        if not isinstance(book, AccountingBookDraft):
            raise InvalidBookAssignment("A non-book exists in preview catalog")
        if (
            book.scope.tenant_id != scope.tenant_id
            or book.scope.company_id != scope.company_id
            or book.scope.legal_entity_id != scope.legal_entity_id
        ):
            raise InvalidBookAssignment("Out-of-scope book in preview catalog")
        if book.id in by_id:
            raise BookAssignmentAmbiguous("Duplicate book identities in preview catalog")
        by_id[book.id] = book

    selected = {}
    seen_ids = set()
    for assignment in assignments:
        if not isinstance(assignment, BookAssignmentCandidate):
            raise InvalidBookAssignment("A non-assignment exists in preview catalog")
        if (
            assignment.scope.tenant_id != scope.tenant_id
            or assignment.scope.company_id != scope.company_id
            or assignment.scope.legal_entity_id != scope.legal_entity_id
        ):
            raise InvalidBookAssignment("Out-of-scope assignment in preview catalog")
        if assignment.id in seen_ids:
            raise BookAssignmentAmbiguous("Duplicate candidate assignment identities")
        seen_ids.add(assignment.id)
        book = by_id.get(assignment.scope.book_id)
        if book is None:
            raise InvalidBookAssignment("Assignment refers to unavailable book draft")
        assignment.require_candidate_compatibility(book)
        if assignment.purpose != purpose or not assignment.effective.contains(as_of):
            continue
        if assignment.scope.book_id in selected:
            raise BookAssignmentAmbiguous("Overlapping active assignments for one book/purpose")
        if not book.effective.contains(as_of):
            raise InvalidBookAssignment("Book validity does not cover requested date")
        selected[book.id] = book

    if not selected:
        raise BookAssignmentMissing("No explicitly assigned book draft for scope/date/purpose")
    return tuple(sorted(selected.values(), key=lambda x: (x.code.value, str(x.id))))
