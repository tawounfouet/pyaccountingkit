"""L04-06: read-only candidate snapshot preview over versioned R&D fixtures.

Not a published C10 endpoint, legal IAM decision or accounting posting right.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from ..domain.accounting_books import (
    BookAssignmentPurpose,
    BookConfigurationCandidateSnapshot,
    BookConfigurationCandidateVersion,
    InvalidBookCandidateVersion,
    NormativeSourceCode,
    preview_normative_reference_history,
    select_book_candidate_version,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from .accounting_book_normative_history import NormativeReferenceClaimsReader
from .accounting_books import (
    BookDraftAuthorization,
    BookDraftPermissionDenied,
    CompanyEntityMembership,
)
from .ports import TrustedPrincipal


@dataclass(frozen=True, slots=True)
class PreviewBookConfigurationSnapshot:
    scope: ConfigurationScope
    purpose: BookAssignmentPurpose
    source: NormativeSourceCode
    as_of: date
    known_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is None:
            raise InvalidBookCandidateVersion("Book-level scope required")
        if not isinstance(self.purpose, BookAssignmentPurpose):
            raise InvalidBookCandidateVersion("Typed purpose required")
        if not isinstance(self.source, NormativeSourceCode):
            raise InvalidBookCandidateVersion("Typed source required")
        if type(self.as_of) is not date:
            raise InvalidBookCandidateVersion("Business date required")
        if (
            type(self.known_at) is not datetime
            or self.known_at.tzinfo is None
            or self.known_at.utcoffset() is None
        ):
            raise InvalidBookCandidateVersion("Timezone-aware known_at required")


class BookCandidateVersionReader(Protocol):
    """A read-only version port, not a signed/published configuration store."""

    def list_for_book(
        self, scope: ConfigurationScope
    ) -> tuple[BookConfigurationCandidateVersion, ...]: ...


class BookCandidateSnapshotPreviewService:
    """Compose bitemporal CANDIDATE version + historical UNVERIFIED norm claim."""

    def __init__(
        self,
        versions: BookCandidateVersionReader,
        normative_statements: NormativeReferenceClaimsReader,
        authorization: BookDraftAuthorization,
        membership: CompanyEntityMembership,
    ) -> None:
        self._versions = versions
        self._statements = normative_statements
        self._authorization = authorization
        self._membership = membership

    def preview(
        self, query: PreviewBookConfigurationSnapshot, *,
        principal: TrustedPrincipal,
    ) -> BookConfigurationCandidateSnapshot:
        if not isinstance(query, PreviewBookConfigurationSnapshot):
            raise TypeError("Expected PreviewBookConfigurationSnapshot")
        if not isinstance(principal, TrustedPrincipal):
            raise BookDraftPermissionDenied("Verified principal required")
        if principal.tenant_id != query.scope.tenant_id:
            raise BookDraftPermissionDenied("Cross-tenant snapshot preview denied")
        self._authorization.require(
            principal=principal,
            action="book.candidate_snapshot.preview",
            scope=query.scope,
        )
        self._membership.require(scope=query.scope)
        version = select_book_candidate_version(
            scope=query.scope,
            purpose=query.purpose,
            as_of=query.as_of,
            known_at=query.known_at,
            versions=self._versions.list_for_book(query.scope),
        )
        claim = preview_normative_reference_history(
            framework=version.binding.framework,
            source=query.source,
            as_of=query.as_of,
            known_at=query.known_at,
            statements=self._statements.list_for_reference(
                version.binding.framework, query.source
            ),
        )
        return BookConfigurationCandidateSnapshot(
            version=version,
            normative_claim=claim,
            as_of=query.as_of,
            known_at=query.known_at,
        )
