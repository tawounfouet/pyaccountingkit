"""L04-07 scoped read-only dependency receipt composition (R&D, never C10)."""

from dataclasses import dataclass
from typing import Protocol

from ..domain.accounting_books import (
    BookDependencyCandidateReadReceipt,
    BookDependencyClaim,
    InvalidBookDependency,
    preview_book_dependency_completeness,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.identifiers import BookCandidateVersionId
from .accounting_book_candidate_snapshots import (
    BookCandidateSnapshotPreviewService,
    PreviewBookConfigurationSnapshot,
)
from .accounting_books import (
    BookDraftAuthorization,
    BookDraftPermissionDenied,
    CompanyEntityMembership,
)
from .ports import TrustedPrincipal


@dataclass(frozen=True, slots=True)
class PreviewBookDependencyReadReceipt:
    """Wrap the exact business-date and knowledge-cutoff candidate query."""

    snapshot_query: PreviewBookConfigurationSnapshot

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_query, PreviewBookConfigurationSnapshot):
            raise InvalidBookDependency("Typed candidate snapshot query required")


class BookDependencyCandidateReader(Protocol):
    """Reads untrusted local claims; NOT a certified Chart/Calendar/Policy API."""

    def list_for_version(
        self, scope: ConfigurationScope, candidate_version_id: BookCandidateVersionId
    ) -> tuple[BookDependencyClaim, ...]: ...


class BookDependencyReadReceiptService:
    """Require separate actions for source snapshot and dependency receipt."""

    def __init__(
        self,
        snapshots: BookCandidateSnapshotPreviewService,
        dependencies: BookDependencyCandidateReader,
        authorization: BookDraftAuthorization,
        membership: CompanyEntityMembership,
    ) -> None:
        self._snapshots = snapshots
        self._dependencies = dependencies
        self._authorization = authorization
        self._membership = membership

    def preview(
        self, query: PreviewBookDependencyReadReceipt, *, principal: TrustedPrincipal
    ) -> BookDependencyCandidateReadReceipt:
        if not isinstance(query, PreviewBookDependencyReadReceipt):
            raise TypeError("Expected PreviewBookDependencyReadReceipt")
        if not isinstance(principal, TrustedPrincipal):
            raise BookDraftPermissionDenied("Verified principal required")
        scope = query.snapshot_query.scope
        if principal.tenant_id != scope.tenant_id:
            raise BookDraftPermissionDenied("Cross-tenant read receipt denied")
        self._authorization.require(
            principal=principal,
            action="book.dependency_receipt.preview",
            scope=scope,
        )
        self._membership.require(scope=scope)
        snapshot = self._snapshots.preview(query.snapshot_query, principal=principal)
        claims = self._dependencies.list_for_version(
            scope, snapshot.version.id
        )
        return preview_book_dependency_completeness(snapshot=snapshot, claims=claims)
