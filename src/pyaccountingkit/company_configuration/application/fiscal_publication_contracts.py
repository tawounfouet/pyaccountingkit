"""L06-04 read-only CQRS view of UNAPPROVED publication intents (R&D)."""

from dataclasses import dataclass
from typing import Protocol

from ..domain.fiscal_calendar.publication_intents import (
    CalendarPublicationContractDiagnostic,
    CalendarPublicationRequestCandidate,
    InvalidCalendarPublicationIntent,
    preview_calendar_publication_contract,
)
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.identifiers import CalendarPublicationIntentId
from .ports import AuthorizationPort, TrustedPrincipal


class CalendarPublicationIntentsReader(Protocol):
    """Read-only candidate data; never a publisher, issuer or Outbox writer."""

    def list_for_scope(
        self, scope: ConfigurationScope
    ) -> tuple[CalendarPublicationRequestCandidate, ...]: ...


@dataclass(frozen=True, slots=True)
class PreviewCalendarPublicationContract:
    scope: ConfigurationScope
    intent_id: CalendarPublicationIntentId

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidCalendarPublicationIntent("Entity-level candidate scope required")
        if not isinstance(self.intent_id, CalendarPublicationIntentId):
            raise InvalidCalendarPublicationIntent("Typed publication intent ID required")


class CalendarPublicationContractPreviewService:
    """Only inventory review; never grants permission or publishes a version."""

    def __init__(
        self, *, reader: CalendarPublicationIntentsReader,
        authorization: AuthorizationPort,
    ) -> None:
        self._reader = reader
        self._authorization = authorization

    def preview(
        self, query: PreviewCalendarPublicationContract, *,
        principal: TrustedPrincipal,
    ) -> CalendarPublicationContractDiagnostic:
        if not isinstance(query, PreviewCalendarPublicationContract):
            raise TypeError("Typed publication candidate query required")
        if not isinstance(principal, TrustedPrincipal):
            raise PermissionError("Unverified publication candidate reader")
        if principal.tenant_id != query.scope.tenant_id:
            raise PermissionError("Cross-tenant publication intent preview denied")
        self._authorization.require(
            principal=principal,
            action="calendar.publication.intent.candidate.preview",
            scope=query.scope,
        )
        values = self._reader.list_for_scope(query.scope)
        if not isinstance(values, tuple):
            raise InvalidCalendarPublicationIntent("Typed immutable publication catalog required")
        selected = []
        for item in values:
            if not isinstance(item, CalendarPublicationRequestCandidate):
                raise InvalidCalendarPublicationIntent("Non-typed publication candidate")
            if item.scope != query.scope:
                raise InvalidCalendarPublicationIntent("Foreign publication scope leaked")
            item.verify_integrity()
            if item.id == query.intent_id:
                selected.append(item)
        if len(selected) != 1:
            raise InvalidCalendarPublicationIntent("Exact publication intent absent/ambiguous")
        return preview_calendar_publication_contract(
            request=selected[0],
            competing_intents=tuple(x for x in values if x.id != query.intent_id),
        )
