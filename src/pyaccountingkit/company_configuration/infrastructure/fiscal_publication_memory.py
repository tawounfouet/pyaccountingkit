"""L06-04 scope-filtered immutable test fixture: no publication writer."""

from ..domain.fiscal_calendar.publication_intents import (
    CalendarPublicationRequestCandidate,
    InvalidCalendarPublicationIntent,
)
from ..domain.shared.accounting_scope import ConfigurationScope


class MemoryCalendarPublicationIntents:
    def __init__(self, intents: tuple[CalendarPublicationRequestCandidate, ...]) -> None:
        if not isinstance(intents, tuple) or any(
            not isinstance(item, CalendarPublicationRequestCandidate) for item in intents
        ):
            raise InvalidCalendarPublicationIntent("Immutable typed publication catalog required")
        self._intents = intents

    def list_for_scope(
        self, scope: ConfigurationScope
    ) -> tuple[CalendarPublicationRequestCandidate, ...]:
        if not isinstance(scope, ConfigurationScope) or scope.book_id is not None:
            raise InvalidCalendarPublicationIntent("Entity-level scope required")
        return tuple(item for item in self._intents if item.scope == scope)
