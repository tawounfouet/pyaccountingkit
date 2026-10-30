"""ORG-5b1 real PostgreSQL: reject lifecycle writes without atomic evidence.

Constraint triggers are deferred to transaction COMMIT. These tests deliberately
exercise direct SQL under the same login used by the Application Service, not an
admin connection or a mocked repository.
"""

import os
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from org_test_seed import (  # noqa: E402
    EvidencedOrganizationSeed as PostgresOrganizationRepository,
)

from pyaccountingkit.company_configuration.application.organization_lifecycle import (  # noqa: E402
    TransitionCompany,
)
from pyaccountingkit.company_configuration.application.organization_lifecycle_service import (  # noqa: E402
    OrganizationLifecycleService,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal  # noqa: E402
from pyaccountingkit.company_configuration.domain.organization.model import (  # noqa: E402
    Company,
    CompanyKind,
    CompanyStatus,
    Establishment,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (  # noqa: E402
    EffectiveInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (  # noqa: E402
    CompanyId,
    EstablishmentId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (  # noqa: E402
    JurisdictionCode,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.organization_lifecycle import (  # noqa: E402
    PostgresOrganizationLifecycleUnitOfWork,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
APP = os.getenv("CC_PG_DSN")
pytestmark = pytest.mark.skipif(
    not (ADMIN and APP),
    reason="ORG-5b1 requires dedicated ephemeral PostgreSQL tenant roles",
)
NOW = datetime(2026, 10, 30, 9, tzinfo=UTC)


class FixedClock:
    def now(self):
        return NOW


class Allow:
    def require(self, *, principal, action, tenant_id):
        assert principal.tenant_id == tenant_id
        assert action == "organization.company.transition"


@pytest.fixture(autouse=True)
def reset_organization_lifecycle():
    if not ADMIN:
        yield
        return

    def wipe():
        with psycopg.connect(ADMIN) as conn:
            conn.execute(
                "TRUNCATE company_configuration.organization_lifecycle_requests,"
                "company_configuration.organization_lifecycle_audit,"
                "company_configuration.organization_lifecycle_outbox,"
                "company_configuration.organizational_company_revisions,"
                "company_configuration.organizational_establishment_revisions"
            )
            conn.execute(
                "TRUNCATE company_configuration.organization_membership_requests,"
                " company_configuration.organization_membership_audit,"
                " company_configuration.organization_membership_outbox,"
                " company_configuration.organizational_membership_revisions,"
                "company_configuration.organizational_legal_identifiers,"
                "company_configuration.organizational_establishments,"
                "company_configuration.organizational_companies"
            )

    wipe()
    yield
    wipe()


def company():
    subject = Company(
        CompanyId.new(), "tenant-a", "Group", CompanyKind.GROUP,
        JurisdictionCode("FR"),
    )
    PostgresOrganizationRepository(APP).add_company(subject)
    return subject


def site():
    entity_id = LegalEntityId.new()
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "INSERT INTO company_configuration.legal_entities "
            "(tenant_id,company_id,entity_id,legal_name,jurisdiction,"
            "functional_currency,revision) VALUES (%s,%s,%s,%s,%s,%s,1)",
            ("tenant-a", uuid4(), entity_id.value, "Legal", "FR", "EUR"),
        )
    subject = Establishment(
        EstablishmentId.new(), "tenant-a", entity_id, "Office",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
    )
    PostgresOrganizationRepository(APP).add_establishment(subject)
    return subject


def counts():
    with psycopg.connect(ADMIN) as conn:
        return tuple(
            conn.execute(
                "SELECT count(*) FROM company_configuration." + table
            ).fetchone()[0]
            for table in (
                "organizational_company_revisions",
                "organizational_establishment_revisions",
                "organization_lifecycle_requests",
                "organization_lifecycle_audit",
                "organization_lifecycle_outbox",
            )
        )


def test_direct_valid_company_transition_without_evidence_fails_at_commit():
    subject = company()
    with pytest.raises(psycopg.errors.CheckViolation, match="requires matching"):
        with psycopg.connect(APP) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_company_revisions "
                "(tenant_id,company_id,revision,status,recorded_at,source_ref) "
                "VALUES (%s,%s,2,'ACTIVE',%s,'direct-sql')",
                ("tenant-a", subject.id.value, NOW),
            )
    assert counts() == (0, 0, 0, 0, 0)


def test_direct_valid_site_transition_without_evidence_fails_at_commit():
    subject = site()
    with pytest.raises(psycopg.errors.CheckViolation, match="requires matching"):
        with psycopg.connect(APP) as conn:
            conn.execute(
                "INSERT INTO "
                "company_configuration.organizational_establishment_revisions "
                "(tenant_id,establishment_id,revision,status,recorded_at,source_ref) "
                "VALUES (%s,%s,2,'ACTIVE',%s,'direct-sql')",
                ("tenant-a", subject.id.value, NOW),
            )
    assert counts() == (0, 0, 0, 0, 0)


def test_lifecycle_with_audit_and_outbox_but_without_request_is_rejected():
    subject = company()
    audit_id, event_id = uuid4(), uuid4()
    with pytest.raises(psycopg.errors.CheckViolation, match="requires matching"):
        with psycopg.connect(APP) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_company_revisions "
                "(tenant_id,company_id,revision,status,recorded_at,source_ref) "
                "VALUES (%s,%s,2,'ACTIVE',%s,'direct')",
                ("tenant-a", subject.id.value, NOW),
            )
            conn.execute(
                "INSERT INTO company_configuration.organization_lifecycle_audit "
                "(record_id,tenant_id,actor_id,action,target_kind,target_id,"
                "before_revision,after_revision,from_status,to_status,reason,"
                "correlation_id,recorded_at) "
                "VALUES (%s,'tenant-a','untrusted',"
                "'organization.company.transition','COMPANY',%s,"
                "1,2,'DRAFT','ACTIVE','direct','corr',%s)",
                (audit_id, subject.id.value, NOW),
            )
            conn.execute(
                "INSERT INTO company_configuration.organization_lifecycle_outbox "
                "(event_id,tenant_id,event_type,schema_version,target_kind,target_id,"
                "revision,from_status,to_status,correlation_id,recorded_at) "
                "VALUES (%s,'tenant-a','organization.company.transition',1,"
                "'COMPANY',%s,2,'DRAFT','ACTIVE','corr',%s)",
                (event_id, subject.id.value, NOW),
            )
    assert counts() == (0, 0, 0, 0, 0)


def test_inconsistent_event_status_cannot_be_used_as_proof():
    subject = company()
    audit_id, event_id = uuid4(), uuid4()
    with pytest.raises(psycopg.errors.CheckViolation, match="requires matching"):
        with psycopg.connect(APP) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_company_revisions "
                "(tenant_id,company_id,revision,status,recorded_at,source_ref) "
                "VALUES (%s,%s,2,'ACTIVE',%s,'direct')",
                ("tenant-a", subject.id.value, NOW),
            )
            conn.execute(
                "INSERT INTO company_configuration.organization_lifecycle_audit "
                "(record_id,tenant_id,actor_id,action,target_kind,target_id,"
                "before_revision,after_revision,from_status,to_status,reason,"
                "correlation_id,recorded_at) "
                "VALUES (%s,'tenant-a','untrusted',"
                "'organization.company.transition','COMPANY',%s,"
                "1,2,'DRAFT','ACTIVE','direct','corr',%s)",
                (audit_id, subject.id.value, NOW),
            )
            conn.execute(
                "INSERT INTO company_configuration.organization_lifecycle_outbox "
                "(event_id,tenant_id,event_type,schema_version,target_kind,target_id,"
                "revision,from_status,to_status,correlation_id,recorded_at) "
                "VALUES (%s,'tenant-a','organization.company.transition',1,"
                "'COMPANY',%s,2,'DRAFT','INACTIVE','corr',%s)",
                (event_id, subject.id.value, NOW),
            )
            conn.execute(
                "INSERT INTO company_configuration.organization_lifecycle_requests "
                "(tenant_id,actor_id,action,request_key,request_digest,target_kind,"
                "target_id,revision,correlation_id,audit_id,event_id) "
                "VALUES ('tenant-a','untrusted','organization.company.transition',"
                "'direct',%s,'COMPANY',%s,2,'corr',%s,%s)",
                ("a" * 64, subject.id.value, audit_id, event_id),
            )
    assert counts() == (0, 0, 0, 0, 0)


def test_normal_authorized_application_transaction_still_commits_three_proofs():
    subject = company()
    service = OrganizationLifecycleService(
        lambda: PostgresOrganizationLifecycleUnitOfWork(APP), Allow(), FixedClock(),
    )
    actor = TrustedPrincipal("operator", "tenant-a")
    command = TransitionCompany(
        "tenant-a", subject.id, CompanyStatus.ACTIVE, 1,
        "board", "request", "correlation", "approved",
    )
    receipt = service.transition_company(command, principal=actor)
    assert receipt.revision == 2
    assert counts() == (1, 0, 1, 1, 1)
    assert service.transition_company(command, principal=actor) == receipt
    assert counts() == (1, 0, 1, 1, 1)
