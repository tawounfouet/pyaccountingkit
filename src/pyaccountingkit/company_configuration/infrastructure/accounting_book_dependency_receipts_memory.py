"""L04-07 process-only dependency fixture, never a source-of-truth registry."""

from ..domain.accounting_books import BookDependencyClaim, InvalidBookDependency
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.identifiers import BookCandidateVersionId


class MemoryBookDependencyClaims:
    """Typed read-only fixture; no publication, ownership, validation or SQL."""

    def __init__(self, claims: tuple[BookDependencyClaim, ...]) -> None:
        if not isinstance(claims, tuple) or any(
            not isinstance(item, BookDependencyClaim) for item in claims
        ):
            raise InvalidBookDependency("Claims require a typed immutable tuple")
        self._claims = claims

    def list_for_version(
        self, scope: ConfigurationScope, candidate_version_id: BookCandidateVersionId
    ) -> tuple[BookDependencyClaim, ...]:
        if (
            not isinstance(scope, ConfigurationScope)
            or scope.book_id is None
            or not isinstance(candidate_version_id, BookCandidateVersionId)
        ):
            raise InvalidBookDependency("Typed book scope and candidate ID required")
        return tuple(
            item for item in self._claims
            if item.scope == scope and item.candidate_version_id == candidate_version_id
        )
