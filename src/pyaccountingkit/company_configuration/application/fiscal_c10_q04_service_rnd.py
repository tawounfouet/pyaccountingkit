"""L06-05 read-only CQRS simulator, not a registered C10-Q04 provider."""

from dataclasses import dataclass

from ..domain.fiscal_calendar.period_controls import ObservationCompleteness
from .fiscal_c10_q04_simulation import (
    SimulatedPeriodStatusQuery,
    SimulatedPeriodStatusResponse,
    simulate_period_status_contract,
)
from .fiscal_calendar_candidate_preview import PreviewBookCalendarCandidate
from .fiscal_period_control_diagnostics import (
    PeriodControlCandidateDiagnosticService,
    PreviewPeriodControlsCandidate,
)
from .ports import AuthorizationPort, TrustedPrincipal


@dataclass(frozen=True, slots=True)
class SimulatePeriodStatusContract:
    query: SimulatedPeriodStatusQuery
    completeness: ObservationCompleteness

    def __post_init__(self) -> None:
        if not isinstance(self.query, SimulatedPeriodStatusQuery):
            raise TypeError("Typed simulation query required")
        if not isinstance(self.completeness, ObservationCompleteness):
            raise TypeError("Explicit unverified completeness required")


class FiscalC10Q04SimulationService:
    """Calls all three *candidate* grants; no live Runtime/Execution adapter."""

    def __init__(
        self, *,
        diagnostics: PeriodControlCandidateDiagnosticService,
        authorization: AuthorizationPort,
    ) -> None:
        self._diagnostics = diagnostics
        self._authorization = authorization

    def simulate(
        self, command: SimulatePeriodStatusContract, *,
        principal: TrustedPrincipal,
    ) -> SimulatedPeriodStatusResponse:
        if not isinstance(command, SimulatePeriodStatusContract):
            raise TypeError("Typed contract simulation request required")
        if not isinstance(principal, TrustedPrincipal):
            raise PermissionError("Unverified candidate simulation principal")
        query = command.query
        if principal.tenant_id != query.book_scope.tenant_id:
            raise PermissionError("Cross-tenant period status simulation denied")
        self._authorization.require(
            principal=principal,
            action="calendar.c10_q04.contract.simulation.preview",
            scope=query.book_scope,
        )
        diagnostic = self._diagnostics.preview(
            PreviewPeriodControlsCandidate(
                PreviewBookCalendarCandidate(
                    query.book_scope, query.posting_date, query.known_at,
                ),
                command.completeness,
            ),
            principal=principal,
        )
        return simulate_period_status_contract(
            query=query, diagnostic=diagnostic,
        )
