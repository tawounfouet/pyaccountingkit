"""L03 Organization bounded context: immutable identities, not accounting posting.

DDD aggregates and Value Objects, with explicit tenant and legal-entity scope.
Membership expresses administrative affiliation, NEVER ownership or control.
No ORM/IO, no book assignment, no implicit current-time resolution.
"""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from enum import StrEnum

from ..shared.effective_interval import EffectiveInterval
from ..shared.errors import InvalidOrganization, VersionConflict
from ..shared.identifiers import CompanyId, EstablishmentId, LegalEntityId, MembershipId
from ..shared.references import CurrencyCode, JurisdictionCode
from .entities import LegalEntity


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise InvalidOrganization(f"{name} must be a nonblank, trimmed string")


def _utc(value: datetime) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidOrganization("recorded_at/known_at must be timezone-aware")
    return value.astimezone(UTC)


def _revision(value: int) -> None:
    if type(value) is not int or value < 1:
        raise InvalidOrganization("revision must be a positive integer")


class CompanyKind(StrEnum):
    """Organizational scope is not automatically a legal person."""

    STANDALONE = "STANDALONE"
    GROUP = "GROUP"


class CompanyStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class EstablishmentStatus(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    CLOSED = "CLOSED"


class MembershipKind(StrEnum):
    """No inference about ownership, participation or consolidation."""

    ADMINISTRATIVE = "ADMINISTRATIVE"
    OPERATIONAL = "OPERATIONAL"


@dataclass(frozen=True, slots=True, eq=False)
class Company:
    id: CompanyId
    tenant_id: str
    name: str
    kind: CompanyKind
    home_country: JurisdictionCode
    base_currency: CurrencyCode | None = None
    status: CompanyStatus = CompanyStatus.DRAFT
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, CompanyId):
            raise InvalidOrganization("Company needs a typed CompanyId")
        _text(self.tenant_id, "tenant_id")
        _text(self.name, "company name")
        if not isinstance(self.kind, CompanyKind):
            raise InvalidOrganization("Explicit company kind required")
        if not isinstance(self.home_country, JurisdictionCode):
            raise InvalidOrganization("Typed home country required")
        if self.base_currency is not None and not isinstance(
            self.base_currency, CurrencyCode
        ):
            raise InvalidOrganization("Typed base currency required")
        if not isinstance(self.status, CompanyStatus):
            raise InvalidOrganization("Explicit company status required")
        _revision(self.revision)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Company):
            return NotImplemented
        return (self.tenant_id, self.id) == (other.tenant_id, other.id)

    def __hash__(self) -> int:
        return hash((self.tenant_id, self.id))

    def rename(self, *, name: str, expected_revision: int) -> "Company":
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise VersionConflict("Company version conflict")
        _text(name, "company name")
        if self.name == name or self.status == CompanyStatus.ARCHIVED:
            raise InvalidOrganization("Company cannot be renamed")
        return replace(self, name=name, revision=self.revision + 1)

    def transition(
        self, *, to: CompanyStatus, expected_revision: int
    ) -> "Company":
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise VersionConflict("Company version conflict")
        allowed = {
            CompanyStatus.DRAFT: {CompanyStatus.ACTIVE},
            CompanyStatus.ACTIVE: {CompanyStatus.INACTIVE},
            CompanyStatus.INACTIVE: {CompanyStatus.ACTIVE, CompanyStatus.ARCHIVED},
            CompanyStatus.ARCHIVED: set(),
        }
        if not isinstance(to, CompanyStatus) or to not in allowed[self.status]:
            raise InvalidOrganization("Illegal company lifecycle transition")
        return replace(self, status=to, revision=self.revision + 1)


@dataclass(frozen=True, slots=True, eq=False)
class Establishment:
    """A dated site of a legal person, without an autonomous accounting book."""

    id: EstablishmentId
    tenant_id: str
    legal_entity_id: LegalEntityId
    name: str
    country: JurisdictionCode
    valid: EffectiveInterval
    status: EstablishmentStatus = EstablishmentStatus.PLANNED
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, EstablishmentId):
            raise InvalidOrganization("Typed EstablishmentId required")
        _text(self.tenant_id, "tenant_id")
        if not isinstance(self.legal_entity_id, LegalEntityId):
            raise InvalidOrganization("Typed legal entity reference required")
        _text(self.name, "establishment name")
        if not isinstance(self.country, JurisdictionCode):
            raise InvalidOrganization("Typed country required")
        if not isinstance(self.valid, EffectiveInterval):
            raise InvalidOrganization("Explicit site effective interval required")
        if not isinstance(self.status, EstablishmentStatus):
            raise InvalidOrganization("Explicit establishment status required")
        _revision(self.revision)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Establishment):
            return NotImplemented
        return (self.tenant_id, self.id) == (other.tenant_id, other.id)

    def __hash__(self) -> int:
        return hash((self.tenant_id, self.id))

    def transition(
        self, *, to: EstablishmentStatus, expected_revision: int
    ) -> "Establishment":
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise VersionConflict("Establishment version conflict")
        allowed = {
            EstablishmentStatus.PLANNED: {EstablishmentStatus.ACTIVE, EstablishmentStatus.CLOSED},
            EstablishmentStatus.ACTIVE: {EstablishmentStatus.INACTIVE, EstablishmentStatus.CLOSED},
            EstablishmentStatus.INACTIVE: {EstablishmentStatus.ACTIVE, EstablishmentStatus.CLOSED},
            EstablishmentStatus.CLOSED: set(),
        }
        if not isinstance(to, EstablishmentStatus) or to not in allowed[self.status]:
            raise InvalidOrganization("Illegal establishment lifecycle transition")
        return replace(self, status=to, revision=self.revision + 1)


@dataclass(frozen=True, slots=True)
class LegalIdentifier:
    """Registry identity with provenance and effective validity, not state verification."""

    tenant_id: str
    legal_entity_id: LegalEntityId
    scheme: str
    value: str
    issuer: str
    jurisdiction: JurisdictionCode
    valid: EffectiveInterval
    source_ref: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.tenant_id, "tenant"), (self.scheme, "scheme"),
            (self.value, "identifier"), (self.issuer, "issuer"),
            (self.source_ref, "source reference")
        ):
            _text(value, field)
        if not isinstance(self.legal_entity_id, LegalEntityId):
            raise InvalidOrganization("LegalIdentifier needs an entity id")
        if not isinstance(self.jurisdiction, JurisdictionCode):
            raise InvalidOrganization("LegalIdentifier needs a jurisdiction")
        if not isinstance(self.valid, EffectiveInterval):
            raise InvalidOrganization("LegalIdentifier needs effective validity")


@dataclass(frozen=True, slots=True, eq=False)
class OrganizationMembership:
    """A time-bounded affiliation; amendments append immutable revisions."""

    id: MembershipId
    tenant_id: str
    company_id: CompanyId
    legal_entity_id: LegalEntityId
    kind: MembershipKind
    exclusive: bool
    valid: EffectiveInterval
    recorded_at: datetime
    source_ref: str
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, MembershipId):
            raise InvalidOrganization("Typed MembershipId required")
        _text(self.tenant_id, "tenant_id")
        if not isinstance(self.company_id, CompanyId):
            raise InvalidOrganization("Typed company id required")
        if not isinstance(self.legal_entity_id, LegalEntityId):
            raise InvalidOrganization("Typed legal entity id required")
        if not isinstance(self.kind, MembershipKind) or type(self.exclusive) is not bool:
            raise InvalidOrganization("Typed kind and exclusivity required")
        if not isinstance(self.valid, EffectiveInterval):
            raise InvalidOrganization("Explicit effective interval required")
        _utc(self.recorded_at)
        _text(self.source_ref, "source reference")
        _revision(self.revision)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrganizationMembership):
            return NotImplemented
        return (self.tenant_id, self.id) == (other.tenant_id, other.id)

    def __hash__(self) -> int:
        return hash((self.tenant_id, self.id))

    def end(
        self, *, effective_end: date, recorded_at: datetime,
        source_ref: str, expected_revision: int,
    ) -> "OrganizationMembership":
        # Deliberately cannot change company/entity/kind by editing a membership.
        if type(expected_revision) is not int or expected_revision != self.revision:
            raise VersionConflict("Membership revision conflict")
        if type(effective_end) is not date or effective_end <= self.valid.start:
            raise InvalidOrganization("Membership end must be after its start")
        if self.valid.end is not None and effective_end > self.valid.end:
            raise InvalidOrganization("Cannot expand membership validity via end")
        if _utc(recorded_at) <= _utc(self.recorded_at):
            raise InvalidOrganization("New knowledge must be strictly later")
        _text(source_ref, "source reference")
        if self.valid.end == effective_end:
            raise InvalidOrganization("Membership already ends on this date")
        return replace(
            self, valid=EffectiveInterval(self.valid.start, effective_end),
            recorded_at=recorded_at, source_ref=source_ref,
            revision=self.revision + 1,
        )


def require_establishment_parent(site: Establishment, entity: LegalEntity) -> None:
    """Referential check for in-memory/application adapters; SQL must also enforce it."""
    if (
        not isinstance(site, Establishment)
        or not isinstance(entity, LegalEntity)
        or site.tenant_id != entity.scope.tenant_id
        or site.legal_entity_id != entity.id
    ):
        raise InvalidOrganization("Establishment has no matching authoritative legal entity")


def require_membership_parents(
    membership: OrganizationMembership, company: Company, entity: LegalEntity,
) -> None:
    """Membership joins existing entities; a second group does not transfer legal ownership."""
    if (
        not isinstance(membership, OrganizationMembership)
        or not isinstance(company, Company)
        or not isinstance(entity, LegalEntity)
        or membership.tenant_id != company.tenant_id
        or membership.tenant_id != entity.scope.tenant_id
        or membership.company_id != company.id
        or membership.legal_entity_id != entity.id
    ):
        raise InvalidOrganization("Membership references must exist in the same tenant")
