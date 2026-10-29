"""L02-07d PostgreSQL owner-only manual incident decision qualification."""

# ruff: noqa: E402

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Barrier, Thread
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from pyaccountingkit.company_configuration.application.privileged_incidents import (
    IncidentDecisionConflict,
    IncidentDecisionRequest,
    PrivilegedIncidentService,
    VerifiedIncidentApproval,
)
from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedAccessDenied,
    PrivilegedRoleRequest,
    VerifiedApproval,
    VerifiedOperator,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.privileged_audit import (
    PostgresPrivilegedAudit,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.privileged_incidents import (
    PostgresPrivilegedIncidentRepository,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.privileged_reconciliation import (
    PostgresPrivilegedReviewRepository,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
pytestmark = pytest.mark.skipif(not (ADMIN and RUNTIME), reason="PostgreSQL owner required")
NOW = datetime(2026, 10, 29, 16, 0, tzinfo=UTC)


class Clock:
    def now(self):
        return NOW


class Identity:
    def __init__(self, tenant="tenant-a", actor="incident-investigator"):
        self.principal = VerifiedOperator(actor, tenant)

    def verify(self, context):
        if context != "verified-control-plane":
            raise PrivilegedAccessDenied("Unverified incident identity")
        return self.principal


class Policy:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def require_decision(self, **kwargs):
        if not self.allowed:
            raise PrivilegedAccessDenied("No incident disposition grant")


class ApprovalProvider:
    def __init__(self, approved):
        self.approved = approved

    def resolve(self, *, reference):
        assert reference == self.approved.approval_id
        return self.approved


def create_incident(*, tenant="tenant-a", terminal=None):
    req = PrivilegedRoleRequest(
        uuid4(), tenant, "cc_runtime_probe", "rotate", "operation-approval", "incident",
    )
    operator = VerifiedOperator("original-operator", tenant)
    approval = VerifiedApproval(
        "operation-approval", "original-checker", req.request_id, tenant,
        req.login_role, "rotate", NOW - timedelta(hours=2), NOW + timedelta(hours=2),
    )
    audit = PostgresPrivilegedAudit(ADMIN)
    audit.record_intent(
        request=req, actor=operator, approval=approval,
        recorded_at=NOW - timedelta(minutes=30),
    )
    result = PostgresPrivilegedReviewRepository(ADMIN).mark_stale(
        tenant_id=tenant, reviewer_id="original-reviewer",
        cutoff=NOW - timedelta(minutes=5), detected_at=NOW, limit=100,
    )
    review = next(row for row in result if row.request_id == req.request_id)
    if terminal:
        audit.record_outcome(request=req, actor=operator, outcome=terminal, recorded_at=NOW)
    return req, review, operator


def build_service(review, *, disposition="ESCALATED", allowed=True, actor=None,
                  approver="incident-checker", tenant="tenant-a"):
    request = IncidentDecisionRequest(
        review.review_id, tenant, disposition, "evidence-repo:incident-124",
        "incident-approval-124", "Separate forensic investigation required",
    )
    approval = VerifiedIncidentApproval(
        request.approval_reference, approver, review.review_id, tenant,
        disposition, request.evidence_reference,
        NOW - timedelta(minutes=3), NOW + timedelta(minutes=10),
    )
    service = PrivilegedIncidentService(
        identity=Identity(tenant=actor or tenant), policy=Policy(allowed),
        approvals=ApprovalProvider(approval),
        repository=PostgresPrivilegedIncidentRepository(ADMIN), clock=Clock(),
    )
    return request, service


def decisions(review_id):
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            "SELECT disposition,observed_outcome,decision_actor_id,checker_id "
            "FROM company_configuration.privileged_incident_decisions WHERE review_id=%s",
            (review_id,),
        ).fetchall()


def test_owner_incident_decision_preserves_unknown_and_sod():
    _, review, _ = create_incident()
    req, svc = build_service(review)
    receipt = svc.decide(req, auth_context="verified-control-plane")
    assert receipt.observed_outcome == "UNKNOWN"
    assert decisions(review.review_id) == [
        ("ESCALATED", "UNKNOWN", "incident-investigator", "incident-checker")
    ]
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.privileged_operation_audit "
            "WHERE request_id=%s AND phase IN ('SUCCEEDED','FAILED','CANCELLED')",
            (review.request_id,),
        ).fetchone()[0] == 0


def test_replayed_decision_does_not_append_or_change_disposition():
    _, review, _ = create_incident()
    req, svc = build_service(review)
    svc.decide(req, auth_context="verified-control-plane")
    with pytest.raises(IncidentDecisionConflict, match="already"):
        svc.decide(replace(req, disposition="ESCALATED"), auth_context="verified-control-plane")
    assert len(decisions(review.review_id)) == 1


def test_foreign_tenant_and_no_grant_are_audited_under_verified_identity():
    _, review, _ = create_incident()
    req, svc = build_service(review, actor="tenant-b")
    with pytest.raises(PrivilegedAccessDenied, match="TENANT_MISMATCH"):
        svc.decide(req, auth_context="verified-control-plane")
    req, svc = build_service(review, allowed=False)
    with pytest.raises(PrivilegedAccessDenied, match="PERMISSION_DENIED"):
        svc.decide(req, auth_context="verified-control-plane")
    assert decisions(review.review_id) == []
    with psycopg.connect(ADMIN) as conn:
        rows = conn.execute(
            "SELECT tenant_id,reason_code FROM company_configuration.privileged_incident_denials "
            "WHERE review_id=%s ORDER BY recorded_at,reason_code", (review.review_id,),
        ).fetchall()
        assert sorted(rows) == sorted([
            ("tenant-b", "TENANT_MISMATCH"), ("tenant-a", "PERMISSION_DENIED"),
        ])


@pytest.mark.parametrize("invalid_person", [
    "original-operator", "original-reviewer", "incident-investigator",
])
def test_checker_cannot_be_original_operator_reviewer_or_self(invalid_person):
    _, review, _ = create_incident()
    req, svc = build_service(review, approver=invalid_person)
    with pytest.raises(PrivilegedAccessDenied):
        svc.decide(req, auth_context="verified-control-plane")
    assert not decisions(review.review_id)


def test_late_terminal_outcome_cannot_be_manual_unknown_resolution():
    _, review, _ = create_incident(terminal="SUCCEEDED")
    req, svc = build_service(review)
    with pytest.raises(IncidentDecisionConflict, match="terminal"):
        svc.decide(req, auth_context="verified-control-plane")
    assert not decisions(review.review_id)


def test_two_concurrent_investigators_cannot_create_duplicate_decisions():
    _, review, _ = create_incident()
    req, svc = build_service(review)
    barrier = Barrier(3)
    results, errors = [], []

    def worker():
        barrier.wait()
        try:
            results.append(svc.decide(req, auth_context="verified-control-plane"))
        except IncidentDecisionConflict as exc:
            errors.append(exc)

    threads = [Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=10)
    assert len(results) == 1 and len(errors) == 1
    assert len(decisions(review.review_id)) == 1


def test_runtime_cannot_read_or_tamper_with_control_plane_audit():
    _, review, _ = create_incident()
    req, svc = build_service(review)
    svc.decide(req, auth_context="verified-control-plane")
    with psycopg.connect(RUNTIME) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM company_configuration.privileged_incident_decisions")
    with psycopg.connect(ADMIN) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "UPDATE company_configuration.privileged_incident_decisions "
                "SET observed_outcome='UNKNOWN' WHERE review_id=%s", (review.review_id,),
            )


def test_migration_checksum_stability_after_new_incident_evidence():
    from pyaccountingkit.company_configuration.infrastructure.postgres.migrate import (
        apply_migrations,
    )

    assert apply_migrations(ADMIN) == []
