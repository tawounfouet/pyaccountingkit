"""Explicit CI-only seeding through the transactionally evidenced registration UoW.

This helper is under tests/, never shipped to production. It replaces older
bare PostgresOrganizationRepository INSERT fixtures in positive SQL tests.
A test fixture actor is NOT a production trusted or authenticated principal.
"""

import os
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from pyaccountingkit.company_configuration.application.organization_membership_evidence import (
    MembershipChangeReceipt,
    MembershipTransactionEvidence,
)
from pyaccountingkit.company_configuration.application.organization_registration import (
    OrganizationEvidence,
    OrganizationRegistrationReceipt,
    OrganizationTargetKind,
)
from pyaccountingkit.company_configuration.domain.organization.model import (
    Company,
    Establishment,
    LegalIdentifier,
    OrganizationMembership,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.infrastructure.postgres import (
    organization_registration,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.organization import (
    PostgresOrganizationRepository,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.organization_membership import (
    PostgresOrganizationMembershipUnitOfWork,
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
        # Explicit test-only mapping from ordinary runtime tenant DSN to the
        # separately provisioned issuer for this registration target kind.
        env_by_kind = {
            OrganizationTargetKind.COMPANY: (
                "CC_PG_ORG_COMPANY_WRITER_DSN", "CC_PG_ORG_COMPANY_WRITER_DSN_B"
            ),
            OrganizationTargetKind.ESTABLISHMENT: (
                "CC_PG_ORG_REGISTRY_WRITER_DSN", "CC_PG_ORG_REGISTRY_WRITER_DSN_B"
            ),
            OrganizationTargetKind.LEGAL_IDENTIFIER: (
                "CC_PG_ORG_REGISTRY_WRITER_DSN", "CC_PG_ORG_REGISTRY_WRITER_DSN_B"
            ),
        }
        writer_a, writer_b = env_by_kind[kind]
        if self._dsn == os.getenv("CC_PG_DSN"):
            dsn = os.getenv(writer_a) or self._dsn
        elif self._dsn == os.getenv("CC_PG_DSN_B"):
            dsn = os.getenv(writer_b) or self._dsn
        else:
            dsn = self._dsn
        with organization_registration.PostgresOrganizationRegistrationUnitOfWork(dsn) as uow:
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

    def append_membership(self, item: OrganizationMembership) -> None:
        """Proof-bearing test fixture, including intentional negative SQL cases."""
        if not isinstance(item, OrganizationMembership):
            raise TypeError("Typed OrganizationMembership required")
        scope = ConfigurationScope(
            item.tenant_id, item.company_id, item.legal_entity_id,
        )
        action = (
            "organization.membership.assign" if item.revision == 1
            else "organization.membership.end"
        )
        receipt = MembershipChangeReceipt(
            membership_id=item.id, company_id=item.company_id,
            legal_entity_id=item.legal_entity_id, revision=item.revision,
            correlation_id=str(uuid4()), audit_id=str(uuid4()), event_id=str(uuid4()),
        )
        evidence = MembershipTransactionEvidence(
            membership=item, receipt=receipt, actor_id="test-only-seed",
            action=action, request_key=str(uuid4()),
            request_digest=sha256(str(uuid4()).encode()).hexdigest(),
            reason="test setup only",
        )
        # CI fixture: issuer credential mapping is independent of the normal
        # L02 tenant writer and never used outside test-only setup.
        if self._dsn == os.getenv("CC_PG_DSN"):
            issuer_dsn = os.getenv("CC_PG_ORG_MEMBERSHIP_WRITER_DSN") or self._dsn
        elif self._dsn == os.getenv("CC_PG_DSN_B"):
            issuer_dsn = os.getenv("CC_PG_ORG_MEMBERSHIP_WRITER_DSN_B") or self._dsn
        else:
            issuer_dsn = self._dsn
        with PostgresOrganizationMembershipUnitOfWork(issuer_dsn) as uow:
            uow.org_memberships.append(scope=scope, membership=item)
            uow.append_membership_evidence(scope=scope, evidence=evidence)
            uow.commit()

    def memberships_at(self, **kwargs):
        return self._legacy.memberships_at(**kwargs)
