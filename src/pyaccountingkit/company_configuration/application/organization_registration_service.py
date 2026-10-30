"""ORG-4b: registration use cases with explicit organization identity and UoW.

No fabricated LegalEntityId for Company creation, no use of L02 evidence
tables, and no external C10 delivery guarantee. Ports enforce DIP.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..domain.shared.digest import ContentDigest
from .organization_registration import (
    OrganizationEvidence,
    OrganizationRegistrationAuthorizationPort,
    OrganizationRegistrationReceipt,
    OrganizationRegistrationUnitOfWork,
    OrganizationTargetKind,
    RegisterCompany,
    RegisterEstablishment,
    RegisterLegalIdentifier,
)
from .ports import ClockPort, TrustedPrincipal
from .service import IdempotencyConflict, PermissionDenied, SystemClock


class OrganizationRegistrationService:
    """One new organization object + request receipt + audit + event per commit."""

    def __init__(
        self,
        uow_factory: Callable[[], OrganizationRegistrationUnitOfWork],
        authorization: OrganizationRegistrationAuthorizationPort,
        clock: ClockPort | None = None,
        *,
        company_uow_factory: Callable[[], OrganizationRegistrationUnitOfWork] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._company_uow_factory = company_uow_factory
        self._authorization = authorization
        self._clock = clock if clock is not None else SystemClock()

    def _run(
        self, *, principal: TrustedPrincipal, action: str, tenant_id: str,
        kind: OrganizationTargetKind, target_id: UUID, company_id: UUID | None,
        legal_entity_id: UUID | None, request_id: str, correlation_id: str,
        reason: str, payload: dict, insert: Callable[[OrganizationRegistrationUnitOfWork], None],
    ) -> OrganizationRegistrationReceipt:
        if not isinstance(principal, TrustedPrincipal) or principal.tenant_id != tenant_id:
            raise PermissionDenied("Trusted principal must belong to registration tenant")
        self._authorization.require(
            principal=principal, action=action, tenant_id=tenant_id
        )
        digest = ContentDigest.from_canonical_json({
            "action": action, "tenant_id": tenant_id, "target_kind": kind.value,
            "target_id": str(target_id), "company_id": str(company_id) if company_id else None,
            "legal_entity_id": str(legal_entity_id) if legal_entity_id else None,
            "reason": reason, "correlation_id": correlation_id, "payload": payload,
        }).hex_sha256
        # Company creation cannot fall back to the broad runtime writer.
        # Its independently provisioned SQL issuer is an explicit composition
        # dependency, never derived from a caller-supplied actor/tenant.
        factory = (
            self._company_uow_factory
            if kind is OrganizationTargetKind.COMPANY and self._company_uow_factory is not None
            else self._uow_factory
        )
        with factory() as uow:
            prior = uow.lookup(
                tenant_id=tenant_id, actor_id=principal.actor_id,
                action=action, request_key=request_id,
            )
            if prior is not None:
                prior_digest, receipt = prior
                if prior_digest != digest:
                    raise IdempotencyConflict("Request key already used for a different payload")
                return receipt
            now = self._clock.now()
            if type(now) is not datetime or now.utcoffset() is None:
                raise ValueError("Clock requires an aware instant")
            now = now.astimezone(UTC)
            receipt = OrganizationRegistrationReceipt(
                tenant_id=tenant_id, target_kind=kind, target_id=target_id,
                revision=1, correlation_id=correlation_id,
                audit_id=uuid4(), event_id=uuid4(),
            )
            insert(uow)
            uow.append_evidence(OrganizationEvidence(
                receipt=receipt, actor_id=principal.actor_id, action=action,
                request_key=request_id, request_digest=digest, reason=reason,
                recorded_at=now, company_id=company_id,
                legal_entity_id=legal_entity_id,
            ))
            uow.commit()
            return receipt

    def register_company(
        self, command: RegisterCompany, *, principal: TrustedPrincipal
    ) -> OrganizationRegistrationReceipt:
        if not isinstance(command, RegisterCompany):
            raise TypeError("Expected RegisterCompany")
        company = command.company
        return self._run(
            principal=principal, action="organization.company.register",
            tenant_id=company.tenant_id, kind=OrganizationTargetKind.COMPANY,
            target_id=company.id.value, company_id=company.id.value,
            legal_entity_id=None, request_id=command.request_id,
            correlation_id=command.correlation_id, reason=command.reason,
            payload={
                "name": company.name, "kind": company.kind.value,
                "home_country": company.home_country.value,
                "base_currency": (
                    company.base_currency.value if company.base_currency else None
                ),
                "status": company.status.value, "revision": company.revision,
            },
            insert=lambda uow: uow.insert_company(company),
        )

    def register_establishment(
        self, command: RegisterEstablishment, *, principal: TrustedPrincipal
    ) -> OrganizationRegistrationReceipt:
        if not isinstance(command, RegisterEstablishment):
            raise TypeError("Expected RegisterEstablishment")
        site = command.establishment
        return self._run(
            principal=principal, action="organization.establishment.register",
            tenant_id=site.tenant_id, kind=OrganizationTargetKind.ESTABLISHMENT,
            target_id=site.id.value, company_id=None,
            legal_entity_id=site.legal_entity_id.value,
            request_id=command.request_id, correlation_id=command.correlation_id,
            reason=command.reason,
            payload={
                "name": site.name, "country": site.country.value,
                "valid_from": site.valid.start.isoformat(),
                "valid_to": site.valid.end.isoformat() if site.valid.end else None,
                "status": site.status.value, "revision": site.revision,
            },
            insert=lambda uow: uow.insert_establishment(site),
        )

    def register_legal_identifier(
        self, command: RegisterLegalIdentifier, *, principal: TrustedPrincipal
    ) -> OrganizationRegistrationReceipt:
        if not isinstance(command, RegisterLegalIdentifier):
            raise TypeError("Expected RegisterLegalIdentifier")
        identifier = command.identifier
        return self._run(
            principal=principal, action="organization.legal_identifier.register",
            tenant_id=identifier.tenant_id, kind=OrganizationTargetKind.LEGAL_IDENTIFIER,
            target_id=command.identifier_id, company_id=None,
            legal_entity_id=identifier.legal_entity_id.value,
            request_id=command.request_id, correlation_id=command.correlation_id,
            reason=command.reason,
            payload={
                "scheme": identifier.scheme, "value": identifier.value,
                "issuer": identifier.issuer, "jurisdiction": identifier.jurisdiction.value,
                "valid_from": identifier.valid.start.isoformat(),
                "valid_to": (
                    identifier.valid.end.isoformat() if identifier.valid.end else None
                ),
                "source_ref": identifier.source_ref,
            },
            insert=lambda uow: uow.insert_legal_identifier(
                command.identifier_id, identifier
            ),
        )
