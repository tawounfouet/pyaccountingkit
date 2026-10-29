"""L03 ORG-4 typed membership commands; no transport identity supplied by caller."""

from dataclasses import dataclass
from datetime import date

from ..domain.organization.model import MembershipKind
from ..domain.shared.accounting_scope import ConfigurationScope
from ..domain.shared.errors import InvalidOrganization
from ..domain.shared.identifiers import MembershipId


def _required(value: str, field: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise InvalidOrganization(f"{field} must be nonblank and trimmed")


@dataclass(frozen=True, slots=True)
class AssignOrganizationMembership:
    """Affiliation does not imply ownership or shared accounting books."""

    scope: ConfigurationScope
    membership_id: MembershipId
    kind: MembershipKind
    exclusive: bool
    valid_from: date
    valid_to: date | None
    source_ref: str
    request_id: str
    correlation_id: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidOrganization("Explicit entity-level scope required")
        if not isinstance(self.membership_id, MembershipId):
            raise InvalidOrganization("Typed membership ID required")
        if not isinstance(self.kind, MembershipKind) or type(self.exclusive) is not bool:
            raise InvalidOrganization("Typed kind and exclusivity required")
        from ..domain.shared.effective_interval import EffectiveInterval

        EffectiveInterval(self.valid_from, self.valid_to)
        for value, name in (
            (self.source_ref, "source_ref"), (self.request_id, "request_id"),
            (self.correlation_id, "correlation_id"), (self.reason, "reason"),
        ):
            _required(value, name)


@dataclass(frozen=True, slots=True)
class EndOrganizationMembership:
    scope: ConfigurationScope
    membership_id: MembershipId
    effective_end: date
    expected_revision: int
    source_ref: str
    request_id: str
    correlation_id: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConfigurationScope) or self.scope.book_id is not None:
            raise InvalidOrganization("Explicit entity-level scope required")
        if not isinstance(self.membership_id, MembershipId):
            raise InvalidOrganization("Typed membership ID required")
        if type(self.effective_end) is not date:
            raise InvalidOrganization("Explicit business effective end required")
        if type(self.expected_revision) is not int or self.expected_revision < 1:
            raise InvalidOrganization("Positive expected membership revision required")
        for value, name in (
            (self.source_ref, "source_ref"), (self.request_id, "request_id"),
            (self.correlation_id, "correlation_id"), (self.reason, "reason"),
        ):
            _required(value, name)
