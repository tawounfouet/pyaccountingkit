"""Process-only L06-03 observation catalog, NOT certified audit or lock source."""

from ..domain.fiscal_calendar.period_controls import (
    InvalidPeriodControlCandidate,
    PeriodLockObservationCandidate,
    PeriodStateObservationCandidate,
    PeriodTransitionDeclarationCandidate,
)
from ..domain.shared.accounting_scope import ConfigurationScope


class MemoryPeriodControlCandidates:
    def __init__(
        self, *, states: tuple[PeriodStateObservationCandidate, ...],
        locks: tuple[PeriodLockObservationCandidate, ...] = (),
        transitions: tuple[PeriodTransitionDeclarationCandidate, ...] = (),
    ) -> None:
        for catalog, kind in (
            (states, PeriodStateObservationCandidate),
            (locks, PeriodLockObservationCandidate),
            (transitions, PeriodTransitionDeclarationCandidate),
        ):
            if not isinstance(catalog, tuple) or any(
                not isinstance(item, kind) for item in catalog
            ):
                raise InvalidPeriodControlCandidate("Immutable typed catalogs required")
        self._states = states
        self._locks = locks
        self._transitions = transitions

    def states_for_period(
        self, scope: ConfigurationScope
    ) -> tuple[PeriodStateObservationCandidate, ...]:
        self._scope(scope)
        return tuple(x for x in self._states if x.book_scope == scope)

    def locks_for_period(
        self, scope: ConfigurationScope
    ) -> tuple[PeriodLockObservationCandidate, ...]:
        self._scope(scope)
        return tuple(x for x in self._locks if x.book_scope == scope)

    def declarations_for_period(
        self, scope: ConfigurationScope
    ) -> tuple[PeriodTransitionDeclarationCandidate, ...]:
        self._scope(scope)
        return tuple(x for x in self._transitions if x.book_scope == scope)

    @staticmethod
    def _scope(value: ConfigurationScope) -> None:
        if not isinstance(value, ConfigurationScope) or value.book_id is None:
            raise InvalidPeriodControlCandidate("Typed book-level scope required")
