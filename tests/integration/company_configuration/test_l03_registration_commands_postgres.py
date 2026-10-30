"""ORG-4b: real PostgreSQL transaction, authorization, replay and outbox proofs."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from pyaccountingkit.company_configuration.application.organization_registration import (  # noqa: E402
    OrganizationTargetKind,
    RegisterCompany,
    RegisterEstablishment,
    RegisterLegalIdentifier,
)
from pyaccountingkit.company_configuration.application.organization_registration_service import (  # noqa: E402
    OrganizationRegistrationService,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal  # noqa: E402
from pyaccountingkit.company_configuration.application.service import (  # noqa: E402
    IdempotencyConflict,
    PermissionDenied,
)
from pyaccountingkit.company_configuration.domain.organization.model import (  # noqa: E402
    Company,
    CompanyKind,
    Establishment,
    LegalIdentifier,
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
from pyaccountingkit.company_configuration.infrastructure.postgres import (  # noqa: E402
    organization_registration,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
APP = os.getenv("CC_PG_DSN")
OTHER = os.getenv("CC_PG_DSN_B")
UNBOUND = os.getenv("CC_PG_UNBOUND_DSN")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, APP, OTHER, UNBOUND)),
    reason="ORG-4b requires PostgreSQL 16 CI and tenant runtime credentials",
)


class FixedClock:
    def now(self):
        return datetime(2026, 10, 29, 12, tzinfo=UTC)


class TenantAuthorization:
    def __init__(self):
        self.allowed: set[tuple[str, str, str]] = set()

    def grant(self, principal, action, tenant_id):
        self.allowed.add((principal.actor_id, action, tenant_id))

    def require(self, *, principal, action, tenant_id):
        if (principal.actor_id, action, tenant_id) not in self.allowed:
            raise PermissionDenied("No explicit organizational registration grant")


@pytest.fixture(autouse=True)
def clean_database():
    if not ADMIN:
        yield
        return

    def clean():
        with psycopg.connect(ADMIN) as conn:
            conn.execute(
                "TRUNCATE company_configuration.organization_command_requests,"
                " company_configuration.organization_command_audit,"
                " company_configuration.organization_command_outbox"
            )
            conn.execute(
                "TRUNCATE company_configuration.organization_membership_requests,"
                " company_configuration.organization_membership_audit,"
                " company_configuration.organization_membership_outbox,"
                " company_configuration.organizational_membership_revisions,"
                " company_configuration.organizational_legal_identifiers,"
                " company_configuration.organizational_establishments,"
                " company_configuration.organizational_companies"
            )
    clean()
    yield
    clean()


def service(*, before_commit=None, dsn=APP, tenant="tenant-a"):
    actor = TrustedPrincipal("org-operator", tenant)
    authorizer = TenantAuthorization()
    for action in (
        "organization.company.register",
        "organization.establishment.register",
        "organization.legal_identifier.register",
    ):
        authorizer.grant(actor, action, tenant)
    svc = OrganizationRegistrationService(
        lambda: organization_registration.PostgresOrganizationRegistrationUnitOfWork(
            dsn, before_commit=before_commit,
        ),
        authorizer, FixedClock(),
    )
    return svc, actor, authorizer


def company():
    return Company(
        CompanyId.new(), "tenant-a", "Research Group",
        CompanyKind.GROUP, JurisdictionCode("FR"),
    )


def register_company(entity, *, key="register-1", reason="board registration"):
    return RegisterCompany(entity, key, "corr-company", reason)


def seed_legal():
    identity = LegalEntityId.new()
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "INSERT INTO company_configuration.legal_entities "
            "(tenant_id,company_id,entity_id,legal_name,jurisdiction,"
            "functional_currency,revision) VALUES (%s,%s,%s,%s,%s,%s,1)",
            ("tenant-a", uuid4(), identity.value, "Business SARL", "FR", "EUR"),
        )
    return identity


def counts():
    with psycopg.connect(ADMIN) as conn:
        return tuple(
            conn.execute(
                "SELECT count(*) FROM company_configuration." + name
            ).fetchone()[0]
            for name in (
                "organizational_companies", "organizational_establishments",
                "organizational_legal_identifiers",
                "organization_command_requests", "organization_command_audit",
                "organization_command_outbox",
            )
        )


def test_company_registration_does_not_require_legal_entity():
    svc, actor, _ = service()
    subject = company()
    receipt = svc.register_company(register_company(subject), principal=actor)
    assert receipt.target_kind == OrganizationTargetKind.COMPANY
    assert receipt.target_id == subject.id.value
    assert counts() == (1, 0, 0, 1, 1, 1)
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT legal_entity_id FROM company_configuration.organization_command_audit "
            "WHERE record_id=%s", (receipt.audit_id,),
        ).fetchone() == (None,)
        assert conn.execute(
            "SELECT target_kind,target_id FROM company_configuration.organization_command_outbox "
            "WHERE event_id=%s", (receipt.event_id,),
        ).fetchone() == ("COMPANY", subject.id.value)
    assert svc.register_company(register_company(subject), principal=actor) == receipt
    assert counts() == (1, 0, 0, 1, 1, 1)
    with pytest.raises(IdempotencyConflict):
        svc.register_company(
            register_company(subject, reason="changed"), principal=actor,
        )
    assert counts() == (1, 0, 0, 1, 1, 1)


def test_establishment_registration_requires_authoritative_legal_parent():
    legal = seed_legal()
    svc, actor, _ = service()
    establishment = Establishment(
        EstablishmentId.new(), "tenant-a", legal, "Office North",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
    )
    receipt = svc.register_establishment(
        RegisterEstablishment(establishment, "site-1", "corr-site", "board vote"),
        principal=actor,
    )
    assert receipt.target_kind == OrganizationTargetKind.ESTABLISHMENT
    assert counts() == (0, 1, 0, 1, 1, 1)
    orphan = Establishment(
        EstablishmentId.new(), "tenant-a", LegalEntityId.new(), "Orphan",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
    )
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        svc.register_establishment(
            RegisterEstablishment(orphan, "site-2", "corr-orphan", "board vote"),
            principal=actor,
        )
    assert counts() == (0, 1, 0, 1, 1, 1)


def test_identifier_registration_collision_rolls_back_its_evidence():
    first_legal, second_legal = seed_legal(), seed_legal()
    svc, actor, _ = service()

    def cmd(legal, key):
        return RegisterLegalIdentifier(
            uuid4(),
            LegalIdentifier(
                "tenant-a", legal, "SIREN", "987654321", "INSEE",
                JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
                "registry",
            ),
            key, "corr-registry", "evidence received",
        )

    accepted = cmd(first_legal, "registry-1")
    result = svc.register_legal_identifier(accepted, principal=actor)
    assert result.target_kind == OrganizationTargetKind.LEGAL_IDENTIFIER
    assert counts() == (0, 0, 1, 1, 1, 1)
    with pytest.raises(psycopg.errors.CheckViolation):
        svc.register_legal_identifier(cmd(second_legal, "registry-2"), principal=actor)
    assert counts() == (0, 0, 1, 1, 1, 1)


def test_authorization_and_cross_tenant_block_all_writes():
    svc, actor, authorizer = service()
    subject = company()
    authorizer.allowed.clear()
    with pytest.raises(PermissionDenied):
        svc.register_company(register_company(subject), principal=actor)
    with pytest.raises(PermissionDenied):
        svc.register_company(
            register_company(subject),
            principal=TrustedPrincipal(actor.actor_id, "tenant-b"),
        )
    assert counts() == (0, 0, 0, 0, 0, 0)


def test_precommit_failure_rolls_back_business_and_evidence():
    def crash():
        raise OSError("registration injected precommit fault")

    svc, actor, _ = service(before_commit=crash)
    with pytest.raises(OSError, match="registration injected"):
        svc.register_company(register_company(company()), principal=actor)
    assert counts() == (0, 0, 0, 0, 0, 0)


def test_concurrent_same_key_returns_original_receipt_without_duplication():
    svc, actor, _ = service()
    command = register_company(company())

    def register(_):
        return svc.register_company(command, principal=actor)

    with ThreadPoolExecutor(max_workers=2) as executor:
        receipts = list(executor.map(register, range(2)))
    assert receipts[0] == receipts[1]
    assert counts() == (1, 0, 0, 1, 1, 1)


def test_other_tenant_and_unbound_role_cannot_read_evidence():
    svc, actor, _ = service()
    svc.register_company(register_company(company()), principal=actor)
    with psycopg.connect(OTHER) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.organization_command_outbox"
        ).fetchone()[0] == 0
    with psycopg.connect(UNBOUND) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.organization_command_outbox"
        ).fetchone()[0] == 0
    with psycopg.connect(APP) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "DELETE FROM company_configuration.organization_command_audit"
            )


def test_direct_company_insert_without_evidence_rejected_at_commit():
    subject = company()
    with pytest.raises(psycopg.errors.CheckViolation, match="requires matching"):
        with psycopg.connect(APP) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_companies "
                "(tenant_id,company_id,name,kind,home_country,status,revision) "
                "VALUES (%s,%s,%s,%s,%s,%s,1)",
                (
                    subject.tenant_id, subject.id.value, subject.name,
                    subject.kind.value, subject.home_country.value,
                    subject.status.value,
                ),
            )
    assert counts() == (0, 0, 0, 0, 0, 0)


def test_direct_establishment_insert_without_evidence_rejected_at_commit():
    legal_id = seed_legal()
    subject = Establishment(
        EstablishmentId.new(), "tenant-a", legal_id, "Unrecorded",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="requires matching"):
        with psycopg.connect(APP) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_establishments "
                "(tenant_id,establishment_id,legal_entity_id,name,country,"
                "valid_from,status,revision) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,1)",
                (
                    subject.tenant_id, subject.id.value, legal_id.value,
                    subject.name, subject.country.value, subject.valid.start,
                    subject.status.value,
                ),
            )
    assert counts() == (0, 0, 0, 0, 0, 0)


def test_direct_legal_identifier_insert_without_evidence_rejected_at_commit():
    legal_id = seed_legal()
    with pytest.raises(psycopg.errors.CheckViolation, match="requires matching"):
        with psycopg.connect(APP) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_legal_identifiers "
                "(tenant_id,identifier_id,legal_entity_id,scheme,value,issuer,"
                "jurisdiction,valid_from,source_ref) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    "tenant-a", uuid4(), legal_id.value, "SIREN", "123456789",
                    "INSEE", "FR", date(2026, 1, 1), "unverified",
                ),
            )
    assert counts() == (0, 0, 0, 0, 0, 0)


def test_direct_registration_cannot_commit_with_only_a_request():
    subject = company()
    with pytest.raises(psycopg.errors.CheckViolation, match="requires matching"):
        with psycopg.connect(APP) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_companies "
                "(tenant_id,company_id,name,kind,home_country,status,revision) "
                "VALUES (%s,%s,'Direct','GROUP','FR','DRAFT',1)",
                ("tenant-a", subject.id.value),
            )
            conn.execute(
                "INSERT INTO company_configuration.organization_command_requests "
                "(tenant_id,actor_id,action,request_key,request_digest,target_kind,"
                "target_id,revision,correlation_id,audit_id,event_id) "
                "VALUES ('tenant-a','untrusted','organization.company.register',"
                "'untrusted-key',%s,'COMPANY',%s,1,'correlation',%s,%s)",
                ("a" * 64, subject.id.value, uuid4(), uuid4()),
            )
    assert counts() == (0, 0, 0, 0, 0, 0)
