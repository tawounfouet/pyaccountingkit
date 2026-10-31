"""L06-02 — read-only book/calendar structural candidate query.

The principal shape and injected fake grant do NOT prove legal book membership,
signed issuer authority, C10-Q04, current period status or posting rights.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from ..domain.fiscal_calendar.versions_assignments import (
    BookCalendarAssignmentCandidate,
    BookCalendarCandidateReadReceipt,
    CalendarVersionCandidate,
    InvalidBookCalendarAssignment,
    preview_book_calendar_candidate,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.identifiers import AccountingPeriodId
from .ports import AuthorizationPort, TrustedPrincipal


class CalendarCandidateVersionsReader(Protocol):
    def list_for_book(
        self, scope: ConfigurationScope
    ) -> tuple[CalendarVersionCandidate, ...]: ...


class BookCalendarAssignmentsReader(Protocol):
    def list_for_book(
        self, scope: ConfigurationScope
    ) -> tuple[BookCalendarAssignmentCandidate, ...]: ...


@dataclass(frozen=True, slots=True)
class PreviewBookCalendarCandidate:
    scope: ConfigurationScope
    as_of: date
    known_at: datetime
    adjustment_period_id: AccountingPeriodId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is None:
            raise InvalidBookCalendarAssignment("Explicit book scope required")
        if type(self.as_of) is not date:
            raise InvalidBookCalendarAssignment("Business date required")
        if type(self.known_at) is not datetime or self.known_at.tzinfo is None or (
            self.known_at.utcoffset() is None
        ):
            raise InvalidBookCalendarAssignment("Timezone-aware known_at required")
        if self.adjustment_period_id is not None and not isinstance(
            self.adjustment_period_id, AccountingPeriodId
        ):
            raise InvalidBookCalendarAssignment("Typed adjustment ID required")


class BookCalendarCandidatePreviewService:
    """Hexagonal R&D query, not a verified authorization or posting endpoint."""

    def __init__(
        self, *, versions: CalendarCandidateVersionsReader,
        assignments: BookCalendarAssignmentsReader,
        authorization: AuthorizationPort,
    ) -> None:
        self._versions = versions
        self._assignments = assignments
        self._authorization = authorization

    def preview(
        self, query: PreviewBookCalendarCandidate, *,
        principal: TrustedPrincipal,
    ) -> BookCalendarCandidateReadReceipt:
        if not isinstance(query, PreviewBookCalendarCandidate):
            raise TypeError("Typed candidate preview query required")
        if not isinstance(principal, TrustedPrincipal):
            raise PermissionError("Unverified fiscal calendar candidate principal")
        if principal.tenant_id != query.scope.tenant_id:
            raise PermissionError("Cross-tenant fiscal calendar preview denied")
        self._authorization.require(
            principal=principal,
            action="calendar.assignment.candidate.preview",
            scope=query.scope,
        )
        return preview_book_calendar_candidate(
            book_scope=query.scope, as_of=query.as_of, known_at=query.known_at,
            assignments=self._assignments.list_for_book(query.scope),
            calendar_versions=self._versions.list_for_book(query.scope),
            adjustment_period_id=query.adjustment_period_id,
        )
