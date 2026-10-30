"""R&D-only immutable assignment fixture; no write/persistence or IAM proof."""

from ..domain.accounting_books import BookAssignmentCandidate, InvalidBookAssignment
from ..domain.shared.accounting_scope import ConfigurationScope


class MemoryBookAssignmentCandidates:
    """Strictly local input fixture, not a production reference catalog."""

    def __init__(self, candidates: tuple[BookAssignmentCandidate, ...]) -> None:
        if not isinstance(candidates, tuple) or any(
            not isinstance(x, BookAssignmentCandidate) for x in candidates
        ):
            raise InvalidBookAssignment("Assignment fixture requires a typed immutable tuple")
        self._candidates = candidates

    def list_for_entity(
        self, scope: ConfigurationScope
    ) -> tuple[BookAssignmentCandidate, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
            raise InvalidBookAssignment("Explicit entity-level scope required")
        return tuple(
            candidate for candidate in self._candidates
            if candidate.scope.tenant_id == scope.tenant_id
            and candidate.scope.company_id == scope.company_id
            and candidate.scope.legal_entity_id == scope.legal_entity_id
        )
