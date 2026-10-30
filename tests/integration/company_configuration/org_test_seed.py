"""Explicit CI-only seeding through the transactionally evidenced registration UoW.

This helper is under tests/, never shipped to production. It replaces older
bare PostgresOrganizationRepository INSERT fixtures in positive SQL tests.
A test fixture actor is NOT a production trusted or authenticated principal.
"""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from pyaccountingkit.company_configuration.application.organization_registration import (
    OrganizationEvidence,
    OrganizationRegistrationReceipt,
    OrganizationTargetKind,
)
from pyaccountingkit.company_configuration.domain.organization.model import (
    Company,
    Establishment,
    LegalIdentifier,
)
from pyaccountingkit.company_configuration.infrastructure.postgres import (
    organization_registration,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.organization import (
    PostgresOrganizationRepository,
)


class EvidencedOrganizationSeed:
    """Use explicitly only where a fixture wants a committed registration."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._legacy = PostgresOrganizationRepository(dsn)

    def _seed(
        self, *,
        tenant_id: str,
        kind: OrganizationTargetKind,
        target_id: UUID,
        company_id: UUID | None,
        legal_entity_id: UUID | None,
        insert,
    ) -> None:
        action = {
            OrganizationTargetKind.COMPANY: "organization.company.register",
            OrganizationTargetKind.ESTABLISHMENT: "organization.establishment.register",
            OrganizationTargetKind.LEGAL_IDENTIFIER: (
                "organization.legal_identifier.register"
            ),
        }[kind]
        receipt = OrganizationRegistrationReceipt(
            tenant_id, kind, target_id, 1, str(uuid4()), uuid4(), uuid4(),
        )
        evidence = OrganizationEvidence(
            receipt, "test-only-seed", action, str(uuid4()),
            sha256(str(uuid4()).encode()).hexdigest(), "test setup only",
            datetime.now(UTC), company_id, legal_entity_id,
        )
        with organization_registration.PostgresOrganizationRegistrationUnitOfWork(self._dsn) as uow:
            insert(uow)
            uow.append_evidence(evidence)
            uow.commit()

    def add_company(self, company: Company) -> None:
        self._seed(
            tenant_id=company.tenant_id,
            kind=OrganizationTargetKind.COMPANY,
            target_id=company.id.value,
            company_id=company.id.value,
            legal_entity_id=None,
            insert=lambda uow: uow.insert_company(company),
        )

    def add_establishment(self, site: Establishment) -> None:
        self._seed(
            tenant_id=site.tenant_id,
            kind=OrganizationTargetKind.ESTABLISHMENT,
            target_id=site.id.value,
            company_id=None,
            legal_entity_id=site.legal_entity_id.value,
            insert=lambda uow: uow.insert_establishment(site),
        )

    def add_legal_identifier(self, item: LegalIdentifier) -> UUID:
        target_id = uuid4()
        self._seed(
            tenant_id=item.tenant_id,
            kind=OrganizationTargetKind.LEGAL_IDENTIFIER,
            target_id=target_id,
            company_id=None,
            legal_entity_id=item.legal_entity_id.value,
            insert=lambda uow: uow.insert_legal_identifier(target_id, item),
        )
        return target_id

    def append_membership(self, item) -> None:
        # ORG-5b2a does not yet cover membership-specific evidence; preserve
        # explicit existing SQL/domain tests for that separate increment.
        self._legacy.append_membership(item)

    def memberships_at(self, **kwargs):
        return self._legacy.memberships_at(**kwargs)
