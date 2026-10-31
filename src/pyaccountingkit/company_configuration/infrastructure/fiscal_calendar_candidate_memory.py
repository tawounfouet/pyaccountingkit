"""L06-02 — scoped, read-only memory fixtures, not published calendars."""

from ..domain.fiscal_calendar.versions_assignments import (
    BookCalendarAssignmentCandidate,
    CalendarVersionCandidate,
    InvalidBookCalendarAssignment,
    InvalidCalendarCandidateVersion,
)
from ..domain.shared.accounting_scope import ConfigurationScope


class MemoryCalendarCandidateVersions:
    def __init__(self, versions: tuple[CalendarVersionCandidate, ...]) -> None:
        if not isinstance(versions, tuple) or any(
            not isinstance(item, CalendarVersionCandidate) for item in versions
        ):
            raise InvalidCalendarCandidateVersion("Immutable candidate versions required")
        self._versions = versions

    def list_for_book(
        self, scope: ConfigurationScope
    ) -> tuple[CalendarVersionCandidate, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is None:
            raise InvalidCalendarCandidateVersion("Book query scope required")
        return tuple(
            value for value in self._versions
            if (
                value.calendar.scope.tenant_id == scope.tenant_id
                and value.calendar.scope.company_id == scope.company_id
                and value.calendar.scope.legal_entity_id == scope.legal_entity_id
            )
        )


class MemoryBookCalendarAssignments:
    def __init__(self, assignments: tuple[BookCalendarAssignmentCandidate, ...]) -> None:
        if not isinstance(assignments, tuple) or any(
            not isinstance(item, BookCalendarAssignmentCandidate) for item in assignments
        ):
            raise InvalidBookCalendarAssignment("Immutable candidate assignments required")
        self._assignments = assignments

    def list_for_book(
        self, scope: ConfigurationScope
    ) -> tuple[BookCalendarAssignmentCandidate, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is None:
            raise InvalidBookCalendarAssignment("Book query scope required")
        return tuple(value for value in self._assignments if value.book_scope == scope)
