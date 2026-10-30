"""ORG-4c real SQL: lifecycle transitions, revisions, replay and rollback."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from pyaccountingkit.company_configuration.application.organization_lifecycle import (  # noqa: E402
    TransitionCompany,
    TransitionEstablishment,
)
from pyaccountingkit.company_configuration.application.organization_lifecycle_service import (  # noqa: E402
    OrganizationLifecycleService,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal  # noqa: E402
from pyaccountingkit.company_configuration.application.service import (  # noqa: E402
    IdempotencyConflict,
    PermissionDenied,
)
from pyaccountingkit.company_configuration.domain.organization.model import (  # noqa: E402
    Company,
    CompanyKind,
    CompanyStatus,
    Establishment,
    EstablishmentStatus,
    MembershipKind,
    OrganizationMembership,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (  # noqa: E402
    EffectiveInterval,
)
from pyaccountingkit.company_configuration.domain.shared.errors import (  # noqa: E402
    InvalidOrganization,
    VersionConflict,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (  # noqa: E402
    CompanyId,
    EstablishmentId,
    LegalEntityId,
    MembershipId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (  # noqa: E402
    JurisdictionCode,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.organization_lifecycle import (  # noqa: E402
    PostgresOrganizationLifecycleUnitOfWork,
)
from org_test_seed import (  # noqa: E402
    EvidencedOrganizationSeed as PostgresOrganizationRepository,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
APP = os.getenv("CC_PG_DSN")
OTHER = os.getenv("CC_PG_DSN_B")
pytestmark = pytest.mark.skipif(
    not (ADMIN and APP and OTHER),
    reason="ORG-4c requires ephemeral PostgreSQL 16 tenant-bound CI roles",
)


class Clock:
    def __init__(self):
        self.instant = datetime(2026, 10, 29, 12, tzinfo=UTC)

    def now(self):
        return self.instant


class AllowList:
    def __init__(self):
        self.allowed = set()

    def grant(self, actor, action):
        self.allowed.add((actor.actor_id, action, actor.tenant_id))

    def require(self, *, principal, action, tenant_id):
        if (principal.actor_id, action, tenant_id) not in self.allowed:
            raise PermissionDenied("Explicit lifecycle grant required")


@pytest.fixture(autouse=True)
def clean_lifecycle():
    if not ADMIN:
        yield
        return

    def reset():
        with psycopg.connect(ADMIN) as conn:
            conn.execute(
                "TRUNCATE company_configuration.organizational_company_revisions,"
                "company_configuration.organizational_establishment_revisions,"
                "company_configuration.organization_lifecycle_requests,"
                "company_configuration.organization_lifecycle_audit,"
                "company_configuration.organization_lifecycle_outbox"
            )
            conn.execute(
                "TRUNCATE company_configuration.organizational_membership_revisions,"
                "company_configuration.organizational_legal_identifiers,"
                "company_configuration.organizational_establishments,"
                "company_configuration.organizational_companies"
            )
    reset()
    yield
    reset()


def setup(*, before_commit=None):
    org = Company(
        CompanyId.new(), "tenant-a", "Research group",
        CompanyKind.GROUP, JurisdictionCode("FR"),
    )
    PostgresOrganizationRepository(APP).add_company(org)
    principal = TrustedPrincipal("owner", "tenant-a")
    auth = AllowList()
    for action in ("organization.company.transition", "organization.establishment.transition"):
        auth.grant(principal, action)
    clock = Clock()
    svc = OrganizationLifecycleService(
        lambda: PostgresOrganizationLifecycleUnitOfWork(APP, before_commit=before_commit),
        auth, clock,
    )
    return org, principal, auth, clock, svc


def company_change(org, status, *, expected=1, key="company-1"):
    return TransitionCompany(
        "tenant-a", org.id, status, expected, "approved-minutes", key,
        "correlation-company", "approved",
    )


def site_change(site, status, *, expected=1, key="site-1"):
    return TransitionEstablishment(
        "tenant-a", site.id, status, expected, "approved-minutes", key,
        "correlation-site", "approved",
    )


def seed_site():
    legal_id = LegalEntityId.new()
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "INSERT INTO company_configuration.legal_entities "
            "(tenant_id,company_id,entity_id,legal_name,jurisdiction,"
            "functional_currency,revision) VALUES (%s,%s,%s,%s,%s,%s,1)",
            ("tenant-a", uuid4(), legal_id.value, "Research legal", "FR", "EUR"),
        )
    site = Establishment(
        EstablishmentId.new(), "tenant-a", legal_id, "Paris",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
    )
    PostgresOrganizationRepository(APP).add_establishment(site)
    return site


def counts(table):
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            "SELECT count(*) FROM company_configuration." + table
        ).fetchone()[0]


def lifecycle_evidence_counts():
    return tuple(counts(table) for table in (
        "organization_lifecycle_requests",
        "organization_lifecycle_audit",
        "organization_lifecycle_outbox",
    ))


def test_company_lifecycle_revision_and_durable_evidence():
    org, actor, _, clock, svc = setup()
    first = svc.transition_company(
        company_change(org, CompanyStatus.ACTIVE), principal=actor,
    )
    assert first.revision == 2 and lifecycle_evidence_counts() == (1, 1, 1)
    with PostgresOrganizationLifecycleUnitOfWork(APP) as uow:
        current = uow.company(tenant_id="tenant-a", company_id=org.id)
        assert (current.status, current.revision) == (CompanyStatus.ACTIVE, 2)
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT status,revision FROM company_configuration.organizational_companies "
            "WHERE company_id=%s", (org.id.value,),
        ).fetchone() == ("DRAFT", 1)
    assert svc.transition_company(
        company_change(org, CompanyStatus.ACTIVE), principal=actor
    ) == first
    assert lifecycle_evidence_counts() == (1, 1, 1)
    with pytest.raises(IdempotencyConflict):
        svc.transition_company(
            company_change(org, CompanyStatus.INACTIVE), principal=actor,
        )
    clock.instant += timedelta(seconds=1)
    second = svc.transition_company(
        company_change(org, CompanyStatus.INACTIVE, expected=2, key="company-2"),
        principal=actor,
    )
    assert second.revision == 3
    assert counts("organizational_company_revisions") == 2
    assert lifecycle_evidence_counts() == (2, 2, 2)
    with pytest.raises(VersionConflict):
        svc.transition_company(
            company_change(org, CompanyStatus.ACTIVE, expected=1, key="stale"),
            principal=actor,
        )
    assert lifecycle_evidence_counts() == (2, 2, 2)


def test_establishment_close_is_terminal_and_preserves_initial_snapshot():
    _, actor, _, clock, svc = setup()
    site = seed_site()
    first = svc.transition_establishment(
        site_change(site, EstablishmentStatus.ACTIVE), principal=actor,
    )
    clock.instant += timedelta(seconds=1)
    second = svc.transition_establishment(
        site_change(site, EstablishmentStatus.CLOSED, expected=2, key="site-close"),
        principal=actor,
    )
    assert (first.revision, second.revision) == (2, 3)
    with PostgresOrganizationLifecycleUnitOfWork(APP) as uow:
        current = uow.establishment(
            tenant_id="tenant-a", establishment_id=site.id,
        )
        assert (current.status, current.revision) == (EstablishmentStatus.CLOSED, 3)
    with pytest.raises(InvalidOrganization):
        svc.transition_establishment(
            site_change(site, EstablishmentStatus.ACTIVE, expected=3, key="reactivate"),
            principal=actor,
        )
    assert counts("organizational_establishment_revisions") == 2


def test_illegal_transition_denial_and_tenant_mismatch_do_not_write():
    org, actor, auth, _, svc = setup()
    with pytest.raises(InvalidOrganization):
        svc.transition_company(
            company_change(org, CompanyStatus.ARCHIVED), principal=actor,
        )
    auth.allowed.clear()
    with pytest.raises(PermissionDenied):
        svc.transition_company(
            company_change(org, CompanyStatus.ACTIVE), principal=actor,
        )
    with pytest.raises(PermissionDenied):
        svc.transition_company(
            company_change(org, CompanyStatus.ACTIVE),
            principal=TrustedPrincipal("owner", "tenant-b"),
        )
    assert counts("organizational_company_revisions") == 0
    assert lifecycle_evidence_counts() == (0, 0, 0)


def test_injected_precommit_crash_rolls_back_revision_and_evidence():
    def crash():
        raise OSError("ORG-4c injected precommit failure")

    org, actor, _, _, svc = setup(before_commit=crash)
    with pytest.raises(OSError, match="ORG-4c"):
        svc.transition_company(
            company_change(org, CompanyStatus.ACTIVE), principal=actor,
        )
    assert counts("organizational_company_revisions") == 0
    assert lifecycle_evidence_counts() == (0, 0, 0)


def test_concurrent_identical_transition_returns_same_receipt():
    org, actor, _, _, svc = setup()
    cmd = company_change(org, CompanyStatus.ACTIVE)
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(
            lambda _: svc.transition_company(cmd, principal=actor), range(2)
        ))
    assert receipts[0] == receipts[1]
    assert counts("organizational_company_revisions") == 1
    assert lifecycle_evidence_counts() == (1, 1, 1)


def test_direct_sql_cannot_forge_invalid_transition_or_mutate_history():
    org, actor, _, _, svc = setup()
    with psycopg.connect(APP) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "INSERT INTO company_configuration.organizational_company_revisions "
                "(tenant_id,company_id,revision,status,recorded_at,source_ref) "
                "VALUES (%s,%s,2,'ARCHIVED',%s,'forged')",
                ("tenant-a", org.id.value, datetime.now(UTC)),
            )
    svc.transition_company(company_change(org, CompanyStatus.ACTIVE), principal=actor)
    with psycopg.connect(APP) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "DELETE FROM company_configuration.organizational_company_revisions"
            )
    with psycopg.connect(OTHER) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.organization_lifecycle_outbox"
        ).fetchone()[0] == 0
    assert lifecycle_evidence_counts() == (1, 1, 1)


def _make_affiliation(org, *, start=date(2026, 1, 1), recorded=None):
    return OrganizationMembership(
        MembershipId.new(), "tenant-a", org.id, LegalEntityId.new(),
        MembershipKind.ADMINISTRATIVE, True,
        EffectiveInterval(start), recorded or datetime(2026, 10, 20, tzinfo=UTC),
        "G3-approved-evidence",
    )


def _inactive_company():
    org, actor, _, clock, service = setup()
    service.transition_company(
        company_change(org, CompanyStatus.ACTIVE), principal=actor,
    )
    clock.instant += timedelta(seconds=1)
    service.transition_company(
        company_change(org, CompanyStatus.INACTIVE, expected=2, key="to-inactive"),
        principal=actor,
    )
    clock.instant += timedelta(seconds=1)
    return org, actor, clock, service


def test_g3_archive_rejects_open_affiliation_and_preserves_evidence():
    org, actor, clock, svc = _inactive_company()
    legal = LegalEntityId.new()
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "INSERT INTO company_configuration.legal_entities "
            "(tenant_id,company_id,entity_id,legal_name,jurisdiction,"
            "functional_currency,revision) VALUES (%s,%s,%s,%s,%s,%s,1)",
            ("tenant-a", uuid4(), legal.value, "Affiliated legal", "FR", "EUR"),
        )
    first = OrganizationMembership(
        MembershipId.new(), "tenant-a", org.id, legal,
        MembershipKind.ADMINISTRATIVE, True,
        EffectiveInterval(date(2026, 1, 1)),
        clock.instant, "board-affiliation",
    )
    store = PostgresOrganizationRepository(APP)
    store.append_membership(first)
    before = lifecycle_evidence_counts()
    with pytest.raises(psycopg.errors.CheckViolation, match="Cannot archive"):
        svc.transition_company(
            company_change(org, CompanyStatus.ARCHIVED, expected=3, key="archive"),
            principal=actor,
        )
    assert counts("organizational_company_revisions") == 2
    assert lifecycle_evidence_counts() == before
    # Validity is half-open: ending by the recorded UTC archival date
    # removes the live/future affiliation without erasing historical revisions.
    clock.instant += timedelta(seconds=1)
    store.append_membership(
        first.end(
            effective_end=clock.instant.date(),
            recorded_at=clock.instant,
            source_ref="cessation-registered",
            expected_revision=1,
        )
    )
    clock.instant += timedelta(seconds=1)
    archived = svc.transition_company(
        company_change(org, CompanyStatus.ARCHIVED, expected=3, key="archive"),
        principal=actor,
    )
    assert archived.revision == 4
    assert lifecycle_evidence_counts() == (3, 3, 3)
    assert counts("organizational_membership_revisions") == 2


def test_g3_archived_company_rejects_new_membership_direct_sql():
    org, actor, clock, svc = _inactive_company()
    svc.transition_company(
        company_change(org, CompanyStatus.ARCHIVED, expected=3, key="archive"),
        principal=actor,
    )
    legal = LegalEntityId.new()
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "INSERT INTO company_configuration.legal_entities "
            "(tenant_id,company_id,entity_id,legal_name,jurisdiction,"
            "functional_currency,revision) VALUES (%s,%s,%s,%s,%s,%s,1)",
            ("tenant-a", uuid4(), legal.value, "Legal", "FR", "EUR"),
        )
    membership = OrganizationMembership(
        MembershipId.new(), "tenant-a", org.id, legal,
        MembershipKind.ADMINISTRATIVE, True,
        EffectiveInterval(date(2027, 1, 1)),
        clock.instant, "backdated-claim",
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="archived company"):
        PostgresOrganizationRepository(APP).append_membership(membership)
    assert counts("organizational_membership_revisions") == 0


def test_g3_concurrent_archive_and_membership_cannot_both_commit():
    org, actor, clock, svc = _inactive_company()
    legal = LegalEntityId.new()
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "INSERT INTO company_configuration.legal_entities "
            "(tenant_id,company_id,entity_id,legal_name,jurisdiction,"
            "functional_currency,revision) VALUES (%s,%s,%s,%s,%s,%s,1)",
            ("tenant-a", uuid4(), legal.value, "Legal", "FR", "EUR"),
        )
    affiliation = OrganizationMembership(
        MembershipId.new(), "tenant-a", org.id, legal,
        MembershipKind.ADMINISTRATIVE, True,
        EffectiveInterval(date(2026, 1, 1)),
        clock.instant, "company-affiliation",
    )

    def race(worker):
        try:
            if worker == "archive":
                svc.transition_company(
                    company_change(org, CompanyStatus.ARCHIVED, expected=3, key="archive"),
                    principal=actor,
                )
            else:
                PostgresOrganizationRepository(APP).append_membership(affiliation)
            return "accepted"
        except psycopg.errors.CheckViolation:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(race, ("archive", "membership")))
    assert sorted(outcomes) == ["accepted", "rejected"]
    archived = counts("organizational_company_revisions") == 3
    open_member = counts("organizational_membership_revisions") == 1
    assert archived != open_member


def test_g3_direct_sql_archival_is_also_guarded():
    org, _, clock, _ = _inactive_company()
    legal = LegalEntityId.new()
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "INSERT INTO company_configuration.legal_entities "
            "(tenant_id,company_id,entity_id,legal_name,jurisdiction,"
            "functional_currency,revision) VALUES (%s,%s,%s,%s,%s,%s,1)",
            ("tenant-a", uuid4(), legal.value, "Legal", "FR", "EUR"),
        )
    PostgresOrganizationRepository(APP).append_membership(
        OrganizationMembership(
            MembershipId.new(), "tenant-a", org.id, legal,
            MembershipKind.OPERATIONAL, True,
            EffectiveInterval(date(2027, 1, 1)), clock.instant,
            "future-affiliation",
        )
    )
    with psycopg.connect(APP) as conn:
        with pytest.raises(psycopg.errors.CheckViolation, match="Cannot archive"):
            conn.execute(
                "INSERT INTO company_configuration.organizational_company_revisions "
                "(tenant_id,company_id,revision,status,recorded_at,source_ref) "
                "VALUES (%s,%s,4,'ARCHIVED',%s,'direct-sql')",
                ("tenant-a", org.id.value, clock.instant),
            )
    assert counts("organizational_company_revisions") == 2
