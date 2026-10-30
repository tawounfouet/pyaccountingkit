"""ORG-4 real PostgreSQL UoW proof: membership + audit + outbox + replay.

CI-only disposable tenant database. No direct production credentials.
"""

import os
from datetime import UTC, date, datetime, timedelta
from threading import Barrier, Thread
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from org_test_seed import (  # noqa: E402
    EvidencedOrganizationSeed as PostgresOrganizationRepository,
)

from pyaccountingkit.company_configuration.application.organization_commands import (  # noqa: E402
    AssignOrganizationMembership,
    EndOrganizationMembership,
)
from pyaccountingkit.company_configuration.application.organization_service import (  # noqa: E402
    OrganizationMembershipService,
)
from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal  # noqa: E402
from pyaccountingkit.company_configuration.application.service import (  # noqa: E402
    IdempotencyConflict,
    PermissionDenied,
)
from pyaccountingkit.company_configuration.domain.organization.model import (  # noqa: E402
    Company,
    CompanyKind,
    MembershipKind,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (  # noqa: E402
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.errors import (  # noqa: E402
    InvalidOrganization,
    VersionConflict,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (  # noqa: E402
    CompanyId,
    LegalEntityId,
    MembershipId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (  # noqa: E402
    JurisdictionCode,
)
from pyaccountingkit.company_configuration.infrastructure.memory import (  # noqa: E402
    MemoryAuthorization,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.adapter import (  # noqa: E402
    PostgresUnitOfWork,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RUNTIME_A = os.getenv("CC_PG_DSN")
RUNTIME_B = os.getenv("CC_PG_DSN_B")
pytestmark = pytest.mark.skipif(
    not (ADMIN and RUNTIME_A and RUNTIME_B),
    reason="ORG-4 integration requires dedicated PostgreSQL CI test roles",
)


class MutableClock:
    def __init__(self, now):
        self.instant = now

    def now(self):
        return self.instant


@pytest.fixture(autouse=True)
def isolated_org_transactions():
    if not ADMIN:
        yield
        return

    def reset():
        with psycopg.connect(ADMIN) as conn:
            conn.execute(
                "TRUNCATE company_configuration.organization_membership_requests,"
                " company_configuration.organization_membership_audit,"
                " company_configuration.organization_membership_outbox,"
                " company_configuration.organizational_membership_revisions,"
                " company_configuration.organizational_legal_identifiers,"
                " company_configuration.organizational_establishments,"
                " company_configuration.organizational_companies"
            )
            conn.execute(
                "TRUNCATE company_configuration.outbox_delivery,"
                " company_configuration.legal_entities,"
                " company_configuration.idempotency_requests,"
                " company_configuration.audit_records,"
                " company_configuration.outbox_events"
            )

    reset()
    yield
    reset()


def setup(*, tenant="tenant-a", before_commit=None):
    company_id, entity_id, membership_id = CompanyId.new(), LegalEntityId.new(), MembershipId.new()
    scope = ConfigurationScope(tenant, company_id, entity_id)
    runtime = RUNTIME_B if tenant == "tenant-b" else RUNTIME_A
    principal = TrustedPrincipal("operator", tenant)
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "INSERT INTO company_configuration.legal_entities "
            "(tenant_id,company_id,entity_id,legal_name,jurisdiction,"
            "functional_currency,revision) VALUES (%s,%s,%s,%s,%s,%s,1)",
            (tenant, uuid4(), entity_id.value, "Company Legal", "FR", "EUR"),
        )
    org = Company(
        company_id, tenant, "Group", CompanyKind.GROUP, JurisdictionCode("FR"),
    )
    PostgresOrganizationRepository(runtime).add_company(org)
    authorization = MemoryAuthorization()
    for action in ("organization.membership.assign", "organization.membership.end"):
        authorization.grant(actor_id=principal.actor_id, action=action, scope=scope)
    clock = MutableClock(datetime(2026, 4, 1, tzinfo=UTC))
    service = OrganizationMembershipService(
        lambda: PostgresUnitOfWork(runtime, before_commit=before_commit),
        authorization, clock,
    )
    return scope, membership_id, principal, authorization, clock, service


def assign(scope, membership_id, *, request_id="assign-1", reason="organization approved"):
    return AssignOrganizationMembership(
        scope=scope, membership_id=membership_id,
        kind=MembershipKind.ADMINISTRATIVE, exclusive=True,
        valid_from=date(2026, 1, 1), valid_to=None, source_ref="board-1",
        request_id=request_id, correlation_id="corr-1", reason=reason,
    )


def end(scope, membership_id, *, expected_revision=1, request_id="end-1"):
    return EndOrganizationMembership(
        scope=scope, membership_id=membership_id, effective_end=date(2026, 3, 1),
        expected_revision=expected_revision, source_ref="board-2", request_id=request_id,
        correlation_id="corr-2", reason="cessation approved",
    )


def evidence_counts():
    with psycopg.connect(ADMIN) as conn:
        return tuple(
            conn.execute("SELECT count(*) FROM company_configuration." + table).fetchone()[0]
            for table in (
                "organizational_membership_revisions",
                "organization_membership_requests",
                "organization_membership_audit",
                "organization_membership_outbox",
            )
        )


def test_assign_is_atomic_and_replay_creates_no_duplicate_evidence():
    scope, mid, actor, _, clock, svc = setup()
    first = svc.assign(assign(scope, mid), principal=actor)
    assert first.membership_id == mid and first.legal_entity_id == scope.legal_entity_id
    assert first.revision == 1
    assert evidence_counts() == (1, 1, 1, 1)
    clock.instant += timedelta(days=1)
    second = svc.assign(assign(scope, mid), principal=actor)
    assert second == first
    assert evidence_counts() == (1, 1, 1, 1)
    with pytest.raises(IdempotencyConflict):
        svc.assign(assign(scope, mid, reason="different"), principal=actor)
    assert evidence_counts() == (1, 1, 1, 1)


def test_end_is_append_only_and_historical_membership_is_queryable():
    scope, mid, actor, _, clock, svc = setup()
    svc.assign(assign(scope, mid), principal=actor)
    clock.instant += timedelta(days=1)
    receipt = svc.end(end(scope, mid), principal=actor)
    assert receipt.revision == 2
    assert evidence_counts() == (2, 2, 2, 2)
    store = PostgresOrganizationRepository(RUNTIME_A)
    old = store.memberships_at(
        tenant_id=scope.tenant_id, legal_entity_id=scope.legal_entity_id,
        effective_on=date(2026, 3, 15), known_at=clock.instant - timedelta(hours=1),
    )
    new = store.memberships_at(
        tenant_id=scope.tenant_id, legal_entity_id=scope.legal_entity_id,
        effective_on=date(2026, 3, 15), known_at=clock.instant,
    )
    assert len(old) == 1 and old[0].revision == 1
    assert new == ()
    assert svc.end(end(scope, mid), principal=actor) == receipt
    assert evidence_counts() == (2, 2, 2, 2)
    with pytest.raises(VersionConflict):
        svc.end(end(scope, mid, request_id="end-stale"), principal=actor)


def test_authorization_and_cross_tenant_mismatch_never_write():
    scope, mid, actor, auth, _, svc = setup()
    auth.revoke(actor_id=actor.actor_id, action="organization.membership.assign", scope=scope)
    with pytest.raises(PermissionDenied):
        svc.assign(assign(scope, mid), principal=actor)
    with pytest.raises(PermissionDenied):
        svc.assign(assign(scope, mid), principal=TrustedPrincipal("operator", "tenant-b"))
    assert evidence_counts() == (0, 0, 0, 0)


def test_injected_precommit_failure_rolls_back_membership_audit_and_outbox():
    def fail():
        raise OSError("injected org4 precommit crash")

    scope, mid, actor, _, _, svc = setup(before_commit=fail)
    with pytest.raises(OSError, match="injected org4"):
        svc.assign(assign(scope, mid), principal=actor)
    assert evidence_counts() == (0, 0, 0, 0)


def test_duplicate_membership_id_cannot_be_assigned_twice():
    scope, mid, actor, _, _, svc = setup()
    svc.assign(assign(scope, mid), principal=actor)
    with pytest.raises(VersionConflict):
        svc.assign(assign(scope, mid, request_id="assign-another"), principal=actor)
    assert evidence_counts() == (1, 1, 1, 1)


def test_concurrent_assign_same_request_is_serialized():
    scope, mid, actor, _, _, svc = setup()
    barrier = Barrier(3)
    outputs = []

    def worker():
        barrier.wait()
        outputs.append(svc.assign(assign(scope, mid), principal=actor))

    threads = [Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=15)
    assert len(outputs) == 2 and outputs[0] == outputs[1]
    assert evidence_counts() == (1, 1, 1, 1)


def test_command_guards_refuse_untyped_or_stale_values():
    scope, mid, _, _, _, _ = setup()
    with pytest.raises(InvalidOrganization):
        EndOrganizationMembership(
            scope=scope, membership_id=mid, effective_end=date(2026, 3, 1),
            expected_revision=True, source_ref="ref", request_id="req",
            correlation_id="corr", reason="test",
        )


def test_direct_valid_membership_insert_without_evidence_fails_at_commit():
    scope, membership_id, _, _, clock, _ = setup()
    with pytest.raises(psycopg.errors.CheckViolation, match="Membership revision requires"):
        with psycopg.connect(RUNTIME_A) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_membership_revisions "
                "(tenant_id,membership_id,revision,company_id,legal_entity_id,"
                "kind,exclusive,valid_from,recorded_at,source_ref) "
                "VALUES (%s,%s,1,%s,%s,'ADMINISTRATIVE',true,%s,%s,'direct')",
                (
                    scope.tenant_id, membership_id.value, scope.company_id.value,
                    scope.legal_entity_id.value, date(2026, 1, 1), clock.instant,
                ),
            )
    assert evidence_counts() == (0, 0, 0, 0)


def test_direct_membership_revision_without_evidence_rolls_back():
    scope, membership_id, actor, _, clock, service = setup()
    service.assign(assign(scope, membership_id), principal=actor)
    clock.instant += timedelta(days=1)
    with pytest.raises(psycopg.errors.CheckViolation, match="Membership revision requires"):
        with psycopg.connect(RUNTIME_A) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_membership_revisions "
                "(tenant_id,membership_id,revision,company_id,legal_entity_id,"
                "kind,exclusive,valid_from,valid_to,recorded_at,source_ref) "
                "VALUES (%s,%s,2,%s,%s,'ADMINISTRATIVE',true,%s,%s,%s,'direct')",
                (
                    scope.tenant_id, membership_id.value, scope.company_id.value,
                    scope.legal_entity_id.value, date(2026, 1, 1),
                    date(2026, 3, 1), clock.instant,
                ),
            )
    assert evidence_counts() == (1, 1, 1, 1)


def test_direct_membership_receipt_without_linked_audit_outbox_fails():
    scope, membership_id, _, _, clock, _ = setup()
    with pytest.raises(psycopg.errors.CheckViolation, match="Membership revision requires"):
        with psycopg.connect(RUNTIME_A) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organizational_membership_revisions "
                "(tenant_id,membership_id,revision,company_id,legal_entity_id,"
                "kind,exclusive,valid_from,recorded_at,source_ref) "
                "VALUES (%s,%s,1,%s,%s,'ADMINISTRATIVE',true,%s,%s,'direct')",
                (
                    scope.tenant_id, membership_id.value, scope.company_id.value,
                    scope.legal_entity_id.value, date(2026, 1, 1), clock.instant,
                ),
            )
            conn.execute(
                "INSERT INTO company_configuration.organization_membership_requests "
                "(tenant_id,actor_id,action,request_key,request_digest,membership_id,"
                "company_id,legal_entity_id,revision,correlation_id,audit_id,event_id)"
                " VALUES (%s,'untrusted','organization.membership.assign',"
                "'direct',%s,%s,%s,%s,1,'corr',%s,%s)",
                (
                    scope.tenant_id, "a" * 64, membership_id.value,
                    scope.company_id.value, scope.legal_entity_id.value,
                    uuid4(), uuid4(),
                ),
            )
    assert evidence_counts() == (0, 0, 0, 0)


def test_membership_outbox_has_unambiguous_typed_target_identity():
    scope, membership_id, principal, _, _, service = setup()
    receipt = service.assign(assign(scope, membership_id), principal=principal)
    assert receipt.membership_id == membership_id
    with psycopg.connect(RUNTIME_A) as conn:
        audit = conn.execute(
            "SELECT membership_id,company_id,legal_entity_id,after_revision "
            "FROM company_configuration.organization_membership_audit "
            "WHERE record_id=%s",
            (receipt.audit_id,),
        ).fetchone()
        event = conn.execute(
            "SELECT membership_id,company_id,legal_entity_id,revision,kind,"
            "exclusive,valid_from,valid_to FROM "
            "company_configuration.organization_membership_outbox "
            "WHERE event_id=%s", (receipt.event_id,),
        ).fetchone()
    assert audit == (
        membership_id.value, scope.company_id.value, scope.legal_entity_id.value, 1,
    )
    assert event == (
        membership_id.value, scope.company_id.value, scope.legal_entity_id.value,
        1, "ADMINISTRATIVE", True, date(2026, 1, 1), None,
    )
    assert evidence_counts() == (1, 1, 1, 1)
