"""L02-07c real PostgreSQL proof: unresolved INTENT requires independent review."""

# ruff: noqa: E402

import os
from datetime import UTC, datetime, timedelta
from threading import Barrier, Thread
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from pyaccountingkit.company_configuration.application.privileged_operations import (  # noqa: E402
    PrivilegedAccessDenied,
    PrivilegedRoleRequest,
    VerifiedApproval,
    VerifiedOperator,
)
from pyaccountingkit.company_configuration.application.privileged_reconciliation import (  # noqa: E402
    PrivilegedReconciliationService,
)
from pyaccountingkit.company_configuration.infrastructure.postgres import (
    privileged_reconciliation,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.privileged_audit import (
    PostgresPrivilegedAudit,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
pytestmark = pytest.mark.skipif(not (ADMIN and RUNTIME), reason="Real owner-only PG required")
NOW = datetime(2026, 10, 29, 15, 0, tzinfo=UTC)


class Clock:
    def now(self):
        return NOW


class Identity:
    def verify(self, context):
        if context != "trusted":
            raise PrivilegedAccessDenied("Missing verified control-plane identity")
        return VerifiedOperator("security-reviewer", "tenant-a")


class Policy:
    def require_review(self, *, principal, tenant_id):
        if principal.actor_id != "security-reviewer" or tenant_id != "tenant-a":
            raise PrivilegedAccessDenied("Review grant is absent")


def service():
    return PrivilegedReconciliationService(
        identity=Identity(), policy=Policy(),
        repository=privileged_reconciliation.PostgresPrivilegedReviewRepository(ADMIN), clock=Clock(),
    )


def seed_intent(*, tenant="tenant-a", minutes_old=20, completed=None):
    req = PrivilegedRoleRequest(
        uuid4(), tenant, "cc_runtime_probe", "rotate", "approved-1", "audit repair"
    )
    actor = VerifiedOperator("operator-test", tenant)
    approval = VerifiedApproval(
        "approved-1", "checker-test", req.request_id, tenant,
        req.login_role, "rotate", NOW - timedelta(hours=2), NOW + timedelta(hours=2)
    )
    audit = PostgresPrivilegedAudit(ADMIN)
    audit.record_intent(
        request=req, actor=actor, approval=approval,
        recorded_at=NOW - timedelta(minutes=minutes_old),
    )
    if completed:
        audit.record_outcome(
            request=req, actor=actor, outcome=completed, recorded_at=NOW,
        )
    return req, actor


def reviews_for(request_id):
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            "SELECT review_reason, observed_outcome, reviewer_id, tenant_id FROM "
            "company_configuration.privileged_reconciliation_reviews WHERE request_id=%s",
            (request_id,),
        ).fetchall()


def test_stale_intent_marked_once_with_unknown_outcome():
    req, _ = seed_intent()
    got = service().review_stale(auth_context="trusted", tenant_id="tenant-a")
    match = [x for x in got if x.request_id == req.request_id]
    assert len(match) == 1 and match[0].observed_outcome == "UNKNOWN"
    assert reviews_for(req.request_id) == [
        ("OUTCOME_MISSING", "UNKNOWN", "security-reviewer", "tenant-a")
    ]
    assert not any(
        x.request_id == req.request_id
        for x in service().review_stale(auth_context="trusted", tenant_id="tenant-a")
    )


def test_recent_intent_is_not_automatically_flagged():
    req, _ = seed_intent(minutes_old=1)
    service().review_stale(auth_context="trusted", tenant_id="tenant-a")
    assert not reviews_for(req.request_id)


@pytest.mark.parametrize("phase", ["SUCCEEDED", "FAILED", "CANCELLED"])
def test_existing_terminal_outcome_never_triggers_manual_review(phase):
    req, _ = seed_intent(completed=phase)
    service().review_stale(auth_context="trusted", tenant_id="tenant-a")
    assert not reviews_for(req.request_id)


def test_foreign_tenant_intent_is_excluded_and_review_authz_is_enforced():
    req, _ = seed_intent(tenant="tenant-b")
    service().review_stale(auth_context="trusted", tenant_id="tenant-a")
    assert not reviews_for(req.request_id)
    with pytest.raises(PrivilegedAccessDenied):
        service().review_stale(auth_context="trusted", tenant_id="tenant-b")
    with pytest.raises(PrivilegedAccessDenied):
        service().review_stale(auth_context="untrusted", tenant_id="tenant-a")


def test_two_reviewers_cannot_double_mark_same_request():
    req, _ = seed_intent()
    barrier = Barrier(3)
    caught = []
    outcomes = []

    def worker():
        barrier.wait()
        try:
            outcomes.extend(service().review_stale(auth_context="trusted", tenant_id="tenant-a"))
        except Exception as exc:
            caught.append(exc)

    threads = [Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=10)
    assert not caught
    assert len(reviews_for(req.request_id)) == 1
    assert len([x for x in outcomes if x.request_id == req.request_id]) == 1


def test_runtime_role_cannot_read_or_mutate_privileged_review():
    req, _ = seed_intent()
    service().review_stale(auth_context="trusted", tenant_id="tenant-a")
    with psycopg.connect(RUNTIME) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM company_configuration.privileged_reconciliation_reviews")
    with psycopg.connect(ADMIN) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "UPDATE company_configuration.privileged_reconciliation_reviews "
                "SET observed_outcome='UNKNOWN' WHERE request_id=%s", (req.request_id,),
            )


def test_review_is_not_a_terminal_result_even_if_late_ddl_outcome_arrives():
    req, actor = seed_intent()
    service().review_stale(auth_context="trusted", tenant_id="tenant-a")
    PostgresPrivilegedAudit(ADMIN).record_outcome(
        request=req, actor=actor, outcome="SUCCEEDED", recorded_at=NOW,
    )
    assert reviews_for(req.request_id)[0][1] == "UNKNOWN"
    assert not any(
        x.request_id == req.request_id
        for x in service().review_stale(auth_context="trusted", tenant_id="tenant-a")
    )


def test_cancelled_outcome_is_terminal_and_exclusive():
    req, actor = seed_intent(completed="CANCELLED")
    with pytest.raises(psycopg.errors.UniqueViolation):
        PostgresPrivilegedAudit(ADMIN).record_outcome(
            request=req, actor=actor, outcome="SUCCEEDED", recorded_at=NOW,
        )
