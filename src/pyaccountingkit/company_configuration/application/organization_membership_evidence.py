"""ORG-5b2b membership-native receipt/evidence, distinct from L02 LegalEntity.

Event type and membership_id identify an affiliation revision. No ownership,
consolidation relationship, or standalone financial book is implied.
"""

from dataclasses import dataclass
from uuid import UUID

from ..domain.organization.model import OrganizationMembership
from ..domain.shared.errors import InvalidOrganization
from ..domain.shared.identifiers import CompanyId, LegalEntityId, MembershipId


@dataclass(frozen=True, slots=True)
class MembershipChangeReceipt:
    membership_id: MembershipId
    company_id: CompanyId
    legal_entity_id: LegalEntityId
    revision: int
    correlation_id: str
    audit_id: str
    event_id: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.membership_id, MembershipId)
            or not isinstance(self.company_id, CompanyId)
            or not isinstance(self.legal_entity_id, LegalEntityId)
            or type(self.revision) is not int
            or self.revision < 1
        ):
            raise InvalidOrganization("Typed membership receipt identity required")
        for field in ("correlation_id", "audit_id", "event_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise InvalidOrganization("Nonblank immutable membership receipt field")
        try:
            UUID(self.audit_id)
            UUID(self.event_id)
        except (ValueError, AttributeError) as error:
            raise InvalidOrganization("Membership evidence requires UUID strings") from error


@dataclass(frozen=True, slots=True)
class MembershipTransactionEvidence:
    membership: OrganizationMembership
    receipt: MembershipChangeReceipt
    actor_id: str
    action: str
    request_key: str
    request_digest: str
    reason: str

    def __post_init__(self) -> None:
        m, r = self.membership, self.receipt
        if not isinstance(m, OrganizationMembership) or not isinstance(
            r, MembershipChangeReceipt
        ):
            raise InvalidOrganization("Typed membership and receipt required")
        if (
            r.membership_id != m.id
            or r.company_id != m.company_id
            or r.legal_entity_id != m.legal_entity_id
            or r.revision != m.revision
            or self.action != (
                "organization.membership.assign" if m.revision == 1
                else "organization.membership.end"
            )
        ):
            raise InvalidOrganization("Evidence must describe this exact membership revision")
        for field in ("actor_id", "request_key", "request_digest", "reason"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value or value != value.strip():
                raise InvalidOrganization("Canonical membership evidence text required")
        if len(self.request_digest) != 64 or any(
            character not in "0123456789abcdef" for character in self.request_digest
        ):
            raise InvalidOrganization("Canonical SHA256 digest required")
