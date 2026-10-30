"""ORG-4c lifecycle command contracts (DDD/CQRS; no HTTP or SQL coupling)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Self
from uuid import UUID

from ..domain.organization.model import (
    Company,
    CompanyStatus,
    Establishment,
    EstablishmentStatus,
)
from ..domain.shared.errors import InvalidOrganization
from ..domain.shared.identifiers import CompanyId, EstablishmentId
from .organization_registration import (
    OrganizationRegistrationAuthorizationPort,
    OrganizationTargetKind,
    _text,
)


@dataclass(frozen=True, slots=True)
class TransitionCompany:
    tenant_id: str
    company_id: CompanyId
    to_status: CompanyStatus
    expected_revision: int
    source_ref: str
    request_id: str
    correlation_id: str
    reason: str

    def __post_init__(self) -> None:
        _text(self.tenant_id, "tenant_id")
        if not isinstance(self.company_id, CompanyId):
            raise InvalidOrganization("Typed CompanyId required")
        if not isinstance(self.to_status, CompanyStatus):
            raise InvalidOrganization("Explicit company status required")
        if type(self.expected_revision) is not int or self.expected_revision < 1:
            raise InvalidOrganization("Positive expected revision required")
        for field in ("source_ref", "request_id", "correlation_id", "reason"):
            _text(getattr(self, field), field)


@dataclass(frozen=True, slots=True)
class TransitionEstablishment:
    tenant_id: str
    establishment_id: EstablishmentId
    to_status: EstablishmentStatus
    expected_revision: int
    source_ref: str
    request_id: str
    correlation_id: str
    reason: str

    def __post_init__(self) -> None:
        _text(self.tenant_id, "tenant_id")
        if not isinstance(self.establishment_id, EstablishmentId):
            raise InvalidOrganization("Typed EstablishmentId required")
        if not isinstance(self.to_status, EstablishmentStatus):
            raise InvalidOrganization("Explicit establishment status required")
        if type(self.expected_revision) is not int or self.expected_revision < 1:
            raise InvalidOrganization("Positive expected revision required")
        for field in ("source_ref", "request_id", "correlation_id", "reason"):
            _text(getattr(self, field), field)


@dataclass(frozen=True, slots=True)
class LifecycleReceipt:
    tenant_id: str
    target_kind: OrganizationTargetKind
    target_id: UUID
    revision: int
    correlation_id: str
    audit_id: UUID
    event_id: UUID

    def __post_init__(self) -> None:
        _text(self.tenant_id, "tenant_id")
        _text(self.correlation_id, "correlation_id")
        if (
            self.target_kind not in (
                OrganizationTargetKind.COMPANY, OrganizationTargetKind.ESTABLISHMENT
            )
            or type(self.target_id) is not UUID
            or type(self.revision) is not int
            or self.revision < 2
            or type(self.audit_id) is not UUID
            or type(self.event_id) is not UUID
        ):
            raise InvalidOrganization("Invalid immutable lifecycle receipt")


@dataclass(frozen=True, slots=True)
class LifecycleEvidence:
    receipt: LifecycleReceipt
    actor_id: str
    action: str
    request_key: str
    request_digest: str
    from_status: str
    to_status: str
    reason: str
    before_revision: int
    recorded_at: datetime

    def __post_init__(self) -> None:
        for name in (
            "actor_id", "action", "request_key", "request_digest",
            "from_status", "to_status", "reason",
        ):
            _text(getattr(self, name), name)
        if (
            not isinstance(self.receipt, LifecycleReceipt)
            or type(self.before_revision) is not int
            or self.before_revision + 1 != self.receipt.revision
            or self.from_status == self.to_status
            or type(self.recorded_at) is not datetime
            or self.recorded_at.tzinfo is None
            or self.recorded_at.utcoffset() is None
        ):
            raise InvalidOrganization("Lifecycle evidence missing actual state transition")


class OrganizationLifecycleUnitOfWork(Protocol):
    def __enter__(self) -> Self: ...
    def __exit__(self, exc_type: object, exc: object, tb: object) -> None: ...

    def lookup(
        self, *, tenant_id: str, actor_id: str, action: str, request_key: str
    ) -> tuple[str, LifecycleReceipt] | None: ...

    def company(self, *, tenant_id: str, company_id: CompanyId) -> Company | None: ...
    def establishment(
        self, *, tenant_id: str, establishment_id: EstablishmentId
    ) -> Establishment | None: ...

    def append_company(self, company: Company, *, recorded_at: datetime,
                       source_ref: str) -> None: ...
    def append_establishment(
        self, site: Establishment, *, recorded_at: datetime, source_ref: str
    ) -> None: ...

    def append_evidence(self, record: LifecycleEvidence) -> None: ...
    def commit(self) -> None: ...


__all__ = [
    "LifecycleEvidence", "LifecycleReceipt", "OrganizationLifecycleUnitOfWork",
    "OrganizationRegistrationAuthorizationPort", "TransitionCompany",
    "TransitionEstablishment",
]
