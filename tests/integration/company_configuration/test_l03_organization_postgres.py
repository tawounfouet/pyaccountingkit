"""L03 ORG-3 real SQL: tenant RLS, parent guards, revision history and collision races."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from pyaccountingkit.company_configuration.domain.organization import (  # noqa: E402
    Company,
    CompanyKind,
    Establishment,
    LegalIdentifier,
    MembershipKind,
    OrganizationMembership,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (  # noqa: E402
    EffectiveInterval,
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
from pyaccountingkit.company_configuration.infrastructure.postgres.tenant_boundary import (  # noqa: E402
    TenantConnectionMismatch,
)
from tests.integration.company_configuration.org_test_seed import (  # noqa: E402
    EvidencedOrganizationSeed as PostgresOrganizationRepository,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
DSN_A = os.getenv("CC_PG_DSN")
DSN_B = os.getenv("CC_PG_DSN_B")
UNBOUND = os.getenv("CC_PG_UNBOUND_DSN")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, DSN_A, DSN_B, UNBOUND)),
    reason="ORG-3 requires ephemeral tenant-bound PostgreSQL CI roles",
)
KNOWN = datetime(2026, 4, 8, tzinfo=UTC)


@pytest.fixture
def clean_organization_database():
    if not ADMIN:
        yield
        return
    # Do NOT truncate legacy legal_entities: test FK/parent compatibility.
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "TRUNCATE company_configuration.organizational_membership_revisions,"
            "company_configuration.organizational_legal_identifiers,"
            "company_configuration.organizational_establishments,"
            "company_configuration.organizational_companies"
        )
    yield
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "TRUNCATE company_configuration.organizational_membership_revisions,"
            "company_configuration.organizational_legal_identifiers,"
            "company_configuration.organizational_establishments,"
            "company_configuration.organizational_companies"
        )


def seed_legal(tenant="tenant-a"):
    company_id, legal_id = uuid4(), uuid4()
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "INSERT INTO company_configuration.legal_entities "
            "(tenant_id,company_id,entity_id,legal_name,jurisdiction,"
            "functional_currency,revision) VALUES (%s,%s,%s,%s,%s,%s,1)",
            (tenant, company_id, legal_id, "Existing legal", "FR", "EUR"),
        )
    return LegalEntityId(legal_id)


def company(tenant="tenant-a"):
    return Company(
        CompanyId.new(), tenant, "Group", CompanyKind.GROUP,
        JurisdictionCode("FR"),
    )


def affiliation(c, legal_id, *, mid=None, end=None, date_known=KNOWN, revision=1):
    return OrganizationMembership(
        mid or MembershipId.new(), c.tenant_id, c.id, legal_id,
        MembershipKind.ADMINISTRATIVE, True,
        EffectiveInterval(date(2026, 1, 1), end),
        date_known, "registry-event", revision,
    )


def test_org_baseline_and_tenant_rls(clean_organization_database):
    legal = seed_legal()
    org = company()
    store = PostgresOrganizationRepository(DSN_A)
    store.add_company(org)
    item = affiliation(org, legal)
    store.append_membership(item)
    visible = store.memberships_at(
        tenant_id="tenant-a", legal_entity_id=legal,
        effective_on=date(2026, 2, 1), known_at=KNOWN,
    )
    assert len(visible) == 1 and visible[0].id == item.id
    with psycopg.connect(DSN_B) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.organizational_companies"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.organizational_membership_revisions"
        ).fetchone()[0] == 0
    with psycopg.connect(UNBOUND) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.organizational_companies"
        ).fetchone()[0] == 0
    with psycopg.connect(DSN_A) as conn:
        conn.execute("SELECT set_config('app.tenant_id','tenant-b',true)")
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.organizational_companies"
        ).fetchone()[0] == 1


def test_legacy_entity_without_company_row_still_works(clean_organization_database):
    legal = seed_legal()
    assert legal.value
    # New organization table must not impose FK on L02 historical company_id.
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.organizational_companies"
        ).fetchone()[0] == 0
        conn.execute("TRUNCATE company_configuration.legal_entities")


def test_cross_tenant_and_nonexistent_parent_rejected(clean_organization_database):
    legal_a = seed_legal()
    org_a = company()
    PostgresOrganizationRepository(DSN_A).add_company(org_a)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        PostgresOrganizationRepository(DSN_A).append_membership(
            affiliation(org_a, LegalEntityId.new())
        )
    with pytest.raises(TenantConnectionMismatch):
        PostgresOrganizationRepository(DSN_B).append_membership(
            affiliation(org_a, legal_a)
        )
    org_b = company("tenant-b")
    with pytest.raises(TenantConnectionMismatch):
        PostgresOrganizationRepository(DSN_A).add_company(org_b)
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.organizational_membership_revisions"
        ).fetchone()[0] == 0


def test_append_only_correction_resolves_as_known(
    clean_organization_database,
):
    legal = seed_legal()
    org = company()
    store = PostgresOrganizationRepository(DSN_A)
    store.add_company(org)
    first = affiliation(org, legal, date_known=KNOWN - timedelta(days=7))
    store.append_membership(first)
    second = first.end(
        effective_end=date(2026, 4, 1), recorded_at=KNOWN,
        source_ref="registered-sale", expected_revision=1,
    )
    store.append_membership(second)
    old_view = store.memberships_at(
        tenant_id="tenant-a", legal_entity_id=legal,
        effective_on=date(2026, 4, 3), known_at=KNOWN - timedelta(days=1),
    )
    assert len(old_view) == 1 and old_view[0].revision == 1
    assert store.memberships_at(
        tenant_id="tenant-a", legal_entity_id=legal,
        effective_on=date(2026, 4, 3), known_at=KNOWN,
    ) == ()
    with psycopg.connect(DSN_A) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "DELETE FROM company_configuration.organizational_membership_revisions"
            )
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.organizational_membership_revisions"
        ).fetchone()[0] == 2


def test_revision_gap_and_reparenting_rejected(clean_organization_database):
    legal = seed_legal()
    first_company, other_company = company(), company()
    store = PostgresOrganizationRepository(DSN_A)
    store.add_company(first_company)
    store.add_company(other_company)
    first = affiliation(first_company, legal)
    store.append_membership(first)
    invalid = affiliation(
        first_company, legal, mid=first.id,
        date_known=KNOWN + timedelta(days=1), revision=3,
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        store.append_membership(invalid)
    invalid = affiliation(
        other_company, legal, mid=first.id,
        date_known=KNOWN + timedelta(days=1), revision=2,
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        store.append_membership(invalid)


def test_exclusive_collisions_are_serialized(
    clean_organization_database,
):
    legal = seed_legal()
    left, right = company(), company()
    store = PostgresOrganizationRepository(DSN_A)
    store.add_company(left)
    store.add_company(right)
    candidates = [affiliation(left, legal), affiliation(right, legal)]

    def insert(item):
        try:
            store.append_membership(item)
            return "ok"
        except psycopg.errors.CheckViolation:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(insert, candidates))
    assert sorted(outcomes) == ["ok", "rejected"]


def test_same_registry_id_other_entity_rejected_by_sql(
    clean_organization_database,
):
    one, two = seed_legal(), seed_legal()
    store = PostgresOrganizationRepository(DSN_A)
    def identifier(entity):
        return LegalIdentifier(
            "tenant-a", entity, "SIREN", "123456789", "INSEE",
            JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
            "state-registry",
        )
    store.add_legal_identifier(identifier(one))
    with pytest.raises(psycopg.errors.CheckViolation):
        store.add_legal_identifier(identifier(two))
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.organizational_legal_identifiers"
        ).fetchone()[0] == 1


def test_establishment_parent_and_immutability(clean_organization_database):
    """A site is not a separate legal person and cannot be orphaned."""
    entity_id = seed_legal()
    store = PostgresOrganizationRepository(DSN_A)
    site = Establishment(
        EstablishmentId.new(), "tenant-a", entity_id, "Paris office",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
    )
    store.add_establishment(site)
    orphan = Establishment(
        EstablishmentId.new(), "tenant-a", LegalEntityId.new(), "Unknown site",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
    )
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        store.add_establishment(orphan)
    with psycopg.connect(DSN_A) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "UPDATE company_configuration.organizational_establishments "
                "SET name='rewritten' WHERE establishment_id=%s",
                (site.id.value,),
            )


def test_registry_collision_is_serialized_under_concurrent_requests(
    clean_organization_database,
):
    """Both actors cannot reserve the same current registry identity."""
    first_id, second_id = seed_legal(), seed_legal()
    store = PostgresOrganizationRepository(DSN_A)

    def insert(entity_id):
        item = LegalIdentifier(
            "tenant-a", entity_id, "SIREN", "987654321", "INSEE",
            JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
            "external-register",
        )
        try:
            store.add_legal_identifier(item)
            return "ok"
        except psycopg.errors.CheckViolation:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(insert, [first_id, second_id]))
    assert sorted(results) == ["ok", "rejected"]
