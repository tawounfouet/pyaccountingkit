"""L06-03 CQRS-only period control diagnostics; never a posting guard."""

from dataclasses import dataclass
from typing import Protocol

from ..domain.fiscal_calendar.period_controls import (
    ObservationCompleteness,
    PeriodControlCandidateDiagnostic,
    PeriodLockObservationCandidate,
    PeriodStateObservationCandidate,
    PeriodTransitionDeclarationCandidate,
    preview_period_controls_candidate,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from .fiscal_calendar_candidate_preview import (
    BookCalendarCandidatePreviewService,
    PreviewBookCalendarCandidate,
)
from .ports import AuthorizationPort, TrustedPrincipal


class PeriodControlCandidateReader(Protocol):
    """Unverified test catalog; not authoritative C10 period state."""

    def states_for_period(
        self, scope: ConfigurationScope
    ) -> tuple[PeriodStateObservationCandidate, ...]: ...

    def locks_for_period(
        self, scope: ConfigurationScope
    ) -> tuple[PeriodLockObservationCandidate, ...]: ...

    def declarations_for_period(
        self, scope: ConfigurationScope
    ) -> tuple[PeriodTransitionDeclarationCandidate, ...]: ...


@dataclass(frozen=True, slots=True)
class PreviewPeriodControlsCandidate:
    calendar_query: PreviewBookCalendarCandidate
    completeness: ObservationCompleteness

    def __post_init__(self) -> None:
        if not isinstance(self.calendar_query, PreviewBookCalendarCandidate):
            raise TypeError("Typed calendar candidate query required")
        if not isinstance(self.completeness, ObservationCompleteness):
            raise TypeError("Explicit unverified catalog completeness required")


class PeriodControlCandidateDiagnosticService:
    """Read-only composition: fake grant + L06-02 exact bitemporal receipt."""

    def __init__(
        self, *,
        calendar_preview: BookCalendarCandidatePreviewService,
        observations: PeriodControlCandidateReader,
        authorization: AuthorizationPort,
    ) -> None:
        self._calendar_preview = calendar_preview
        self._observations = observations
        self._authorization = authorization

    def preview(
        self, query: PreviewPeriodControlsCandidate, *,
        principal: TrustedPrincipal,
    ) -> PeriodControlCandidateDiagnostic:
        if not isinstance(query, PreviewPeriodControlsCandidate):
            raise TypeError("Typed period diagnostic query required")
        if not isinstance(principal, TrustedPrincipal):
            raise PermissionError("Unverified candidate diagnostics principal")
        scope = query.calendar_query.scope
        if principal.tenant_id != scope.tenant_id:
            raise PermissionError("Cross-tenant period diagnostics denied")
        self._authorization.require(
            principal=principal,
            action="calendar.period.controls.candidate.preview",
            scope=scope,
        )
        receipt = self._calendar_preview.preview(
            query.calendar_query, principal=principal,
        )
        return preview_period_controls_candidate(
            book_receipt=receipt,
            states=self._observations.states_for_period(scope),
            locks=self._observations.locks_for_period(scope),
            transitions=self._observations.declarations_for_period(scope),
            completeness=query.completeness,
        )
