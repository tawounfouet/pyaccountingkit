"""ORG-4b register commands and ports: company != legal entity != establishment.

Tenant-level registration authorization is explicit and must be supplied through
a trusted authorization adapter. This is not a public API or production IAM.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, Self
from uuid import UUID

from ..domain.organization.model import Company, Establishment, LegalIdentifier
from ..domain.shared.errors import InvalidOrganization
from .ports import TrustedPrincipal


def _text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise InvalidOrganization(f"{field} must be nonblank and trimmed")


class OrganizationTargetKind(StrEnum):
    COMPANY = "COMPANY"
    ESTABLISHMENT = "ESTABLISHMENT"
    LEGAL_IDENTIFIER = "LEGAL_IDENTIFIER"


@dataclass(frozen=True, slots=True)
class RegisterCompany:
    company: Company
    request_id: str
    correlation_id: str
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.company, Company) or self.company.revision != 1:
            raise InvalidOrganization("RegisterCompany expects a new Company")
        for field in ("request_id", "correlation_id", "reason"):
            _text(getattr(self, field), field)


@dataclass(frozen=True, slots=True)
class RegisterEstablishment:
    establishment: Establishment
    request_id: str
    correlation_id: str
    reason: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.establishment, Establishment)
            or self.establishment.revision != 1
        ):
            raise InvalidOrganization("RegisterEstablishment expects a new establishment")
        for field in ("request_id", "correlation_id", "reason"):
            _text(getattr(self, field), field)


@dataclass(frozen=True, slots=True)
class RegisterLegalIdentifier:
    identifier_id: UUID
    identifier: LegalIdentifier
    request_id: str
    correlation_id: str
    reason: str

    def __post_init__(self) -> None:
        if type(self.identifier_id) is not UUID or not isinstance(
            self.identifier, LegalIdentifier
        ):
            raise InvalidOrganization("Explicit UUID and LegalIdentifier required")
        for field in ("request_id", "correlation_id", "reason"):
            _text(getattr(self, field), field)


@dataclass(frozen=True, slots=True)
class OrganizationRegistrationReceipt:
    tenant_id: str
    target_kind: OrganizationTargetKind
    target_id: UUID
    revision: int
    correlation_id: str
    audit_id: UUID
    event_id: UUID

    def __post_init__(self) -> None:
        _text(self.tenant_id, "tenant_id")
        if (
            not isinstance(self.target_kind, OrganizationTargetKind)
            or type(self.target_id) is not UUID
            or self.revision != 1
            or type(self.audit_id) is not UUID
            or type(self.event_id) is not UUID
        ):
            raise InvalidOrganization("Invalid organization registration receipt")
        _text(self.correlation_id, "correlation_id")


@dataclass(frozen=True, slots=True)
class OrganizationEvidence:
    receipt: OrganizationRegistrationReceipt
    actor_id: str
    action: str
    request_key: str
    request_digest: str
    reason: str
    recorded_at: datetime
    company_id: UUID | None
    legal_entity_id: UUID | None

    def __post_init__(self) -> None:
        for field in ("actor_id", "action", "request_key", "request_digest", "reason"):
            _text(getattr(self, field), field)
        if (
            type(self.recorded_at) is not datetime
            or self.recorded_at.utcoffset() is None
            or self.recorded_at.astimezone(UTC) != self.recorded_at
        ):
            raise InvalidOrganization("Explicit timezone-aware recorded instant required")
        for value in (self.company_id, self.legal_entity_id):
            if value is not None and type(value) is not UUID:
                raise InvalidOrganization("Explicit typed organization reference required")


class OrganizationRegistrationAuthorizationPort(Protocol):
    def require(
        self, *, principal: TrustedPrincipal, action: str, tenant_id: str
    ) -> None: ...


class OrganizationRegistrationUnitOfWork(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc: object, tb: object) -> None: ...

    def lookup(
        self, *, tenant_id: str, actor_id: str, action: str, request_key: str
    ) -> tuple[str, OrganizationRegistrationReceipt] | None: ...

    def insert_company(self, company: Company) -> None: ...
    def insert_establishment(self, establishment: Establishment) -> None: ...
    def insert_legal_identifier(
        self, identifier_id: UUID, identifier: LegalIdentifier
    ) -> None: ...

    def append_evidence(self, evidence: OrganizationEvidence) -> None: ...
    def commit(self) -> None: ...
