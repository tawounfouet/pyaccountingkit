"""Real PostgreSQL proof: restricted metrics and approved DEAD-letter re-drive."""
# ruff: noqa: E402

import os
from datetime import UTC, datetime, timedelta
from threading import Barrier, Thread
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from test_delegated_control_plane_postgres import account  # noqa: F401

from pyaccountingkit.company_configuration.application.iam_ack_recovery import (
    RedriveRequest,
    VerifiedRedriveApproval,
)
from pyaccountingkit.company_configuration.application.privileged_operations import VerifiedOperator
from pyaccountingkit.company_configuration.infrastructure.iam.revocation import (
    VerifiedIamRevocation,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.iam_ack_operations import (
    PostgresIamAckApprovalGrants,
    PostgresIamAckMetrics,
    PostgresIamDeadAckRecovery,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.iam_revocation import (
    PostgresIamRevocationRepository,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
IAM = os.getenv("CC_PG_IAM_REVOCATION_DSN")
DELIVERY = os.getenv("CC_PG_IAM_DELIVERY_DSN")
RECOVERY = os.getenv("CC_PG_IAM_RECOVERY_DSN")
APPROVAL_WRITER = os.getenv("CC_PG_IAM_APPROVAL_WRITER_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
CONTROL = os.getenv("CC_PG_CONTROL_PLANE_DSN")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, IAM, DELIVERY, RECOVERY, APPROVAL_WRITER, RUNTIME, CONTROL)),
    reason="Dedicated SQL recovery/delivery IAM roles required",
)


_created_dead_events = []


@pytest.fixture(autouse=True)
def cleanup_dead_letter_test_events():
    # L02-07k tests share this database: never leave reactivated RETRY items
    # to be claimed by unrelated delivery tests later in the suite.
    first = len(_created_dead_events)
    yield
    new_ids = _created_dead_events[first:]
    if new_ids and ADMIN:
        with psycopg.connect(ADMIN) as conn:
            conn.execute(
                "UPDATE company_configuration.privileged_iam_ack_outbox "
                "SET state='DELIVERED',lease_token=NULL,lease_until=NULL, "
                "delivered_at=clock_timestamp(),error_code=NULL "
                "WHERE event_id=ANY(%s::uuid[])", (new_ids,),
            )


def make_dead(role):
    item = VerifiedIamRevocation(
        uuid4(), uuid4(), "tenant-a", role, "rotate", "issuer", "kid", "revoker",
        "a" * 64,
    )
    assert PostgresIamRevocationRepository(IAM).apply(item) == "TOMBSTONED"
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE company_configuration.privileged_iam_ack_outbox SET "
            "state='DEAD',attempts=5,error_code='HTTP_REJECTED' "
            "WHERE event_id=%s", (item.event_id,),
        )
    _created_dead_events.append(item.event_id)
    return item


def read_state(event_id):
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            "SELECT state,attempts,redrive_count,error_code FROM "
            "company_configuration.privileged_iam_ack_outbox WHERE event_id=%s",
            (event_id,),
        ).fetchone()


def req(item, approval=None):
    if approval is None:
        approval = f"independent-approval-{uuid4()}"
    return RedriveRequest(
        item.event_id, item.request_id, "tenant-a", approval,
        "incident-evidence-123", "PROVIDER_RECOVERED",
    )



def issue_approval(request, *, actor_id="investigator", checker_id="checker"):
    """CI-only simulation of an independent signed/authorized approval source."""
    now = datetime.now(UTC)
    approval = VerifiedRedriveApproval(
        request.approval_reference, checker_id, request.event_id, request.request_id,
        request.tenant_id, request.evidence_reference, request.reason_code,
        now - timedelta(seconds=5), now + timedelta(minutes=2),
    )
    return PostgresIamAckApprovalGrants(APPROVAL_WRITER).issue(
        request,
        actor=VerifiedOperator(actor_id, request.tenant_id),
        approval=approval,
        now=now,
    )


def test_recovery_reactivates_dead_with_append_only_decision(request):
    role, _ = request.getfixturevalue("account")
    item = make_dead(role)
    repo = PostgresIamDeadAckRecovery(RECOVERY)
    assert any(row.event_id == item.event_id for row in repo.list_dead("tenant-a", 20))
    assert repo.list_dead("tenant-b", 20) == ()
    approved = req(item)
    assert issue_approval(approved) == 1
    assert repo.redrive(approved, actor_id="investigator", approver_id="checker") == 1
    assert read_state(item.event_id) == ("RETRY", 0, 1, None)
    with psycopg.connect(ADMIN) as conn:
        row = conn.execute(
            "SELECT actor_id,approver_id,redrive_number,previous_error_code "
            "FROM company_configuration.privileged_iam_ack_redrive_decisions "
            "WHERE event_id=%s", (item.event_id,),
        ).fetchone()
        assert row == ("investigator", "checker", 1, "HTTP_REJECTED")
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "UPDATE company_configuration.privileged_iam_ack_redrive_decisions "
                "SET reason_code='INCIDENT_REVIEWED' WHERE event_id=%s",
                (item.event_id,),
            )


def test_recovery_rejects_wrong_tenant_same_actor_and_replay(request):
    role, _ = request.getfixturevalue("account")
    item = make_dead(role)
    repo = PostgresIamDeadAckRecovery(RECOVERY)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        repo.redrive(req(item), actor_id="same", approver_id="same")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        repo.redrive(
            RedriveRequest(item.event_id, item.request_id, "tenant-b", "approval-b",
                           "evidence", "PROVIDER_RECOVERED"),
            actor_id="operator", approver_id="checker",
        )
    allowed = req(item)
    assert issue_approval(allowed, actor_id="operator") == 1
    assert repo.redrive(allowed, actor_id="operator", approver_id="checker") == 1
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        repo.redrive(req(item), actor_id="operator", approver_id="checker")


def test_recovery_requires_new_approval_and_has_two_redrive_limit(request):
    role, _ = request.getfixturevalue("account")
    item = make_dead(role)
    repo = PostgresIamDeadAckRecovery(RECOVERY)
    original = req(item)
    assert issue_approval(original, actor_id="operator") == 1
    assert repo.redrive(original, actor_id="operator", approver_id="checker") == 1
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE company_configuration.privileged_iam_ack_outbox SET "
            "state='DEAD', attempts=5, error_code='HTTP_REJECTED' WHERE event_id=%s",
            (item.event_id,),
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        repo.redrive(original, actor_id="operator", approver_id="checker")
    second = req(item)
    assert issue_approval(second, actor_id="operator") == 2
    assert repo.redrive(second, actor_id="operator", approver_id="checker") == 2
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE company_configuration.privileged_iam_ack_outbox SET "
            "state='DEAD',attempts=5,error_code='HTTP_REJECTED' WHERE event_id=%s",
            (item.event_id,),
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        repo.redrive(
            req(item),
            actor_id="operator", approver_id="checker",
        )
    assert read_state(item.event_id)[2] == 2


def test_delivery_can_only_read_aggregate_metrics_not_dlq_rows(request):
    role, _ = request.getfixturevalue("account")
    make_dead(role)
    snapshot = PostgresIamAckMetrics(DELIVERY).snapshot()
    assert snapshot.dead >= 1
    assert snapshot.due_count >= 0 and snapshot.oldest_open_seconds >= 0
    for dsn in (RUNTIME, CONTROL, IAM):
        with psycopg.connect(dsn) as conn:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute("SELECT * FROM company_configuration.cp_iam_ack_metrics()")
    with psycopg.connect(DELIVERY) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM company_configuration.cp_list_dead_iam_acks(%s,1)",
                         ("tenant-a",))


def test_recovery_login_cannot_change_delivery_or_roles(request):
    role, _ = request.getfixturevalue("account")
    item = make_dead(role)
    with psycopg.connect(RECOVERY) as conn:
        assert conn.execute(
            "SELECT session_user,rolsuper,rolcreaterole,rolbypassrls "
            "FROM pg_roles WHERE rolname=session_user"
        ).fetchone() == ("cc_iam_recovery", False, False, False)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM company_configuration.privileged_iam_ack_outbox")
    with psycopg.connect(RECOVERY) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM company_configuration.cp_claim_iam_ack(1)")
    for dsn in (RUNTIME, CONTROL, DELIVERY):
        with psycopg.connect(dsn) as conn:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(
                    "SELECT company_configuration.cp_redrive_dead_iam_ack("
                    "%s,%s,%s,%s,%s,%s,%s,%s)",
                    (item.event_id,item.request_id,"tenant-a","actor","checker",
                     "approval","PROVIDER_RECOVERED","evidence"),
                )


def test_competing_recovery_reviewers_cannot_both_redrive(request):
    role, _ = request.getfixturevalue("account")
    item = make_dead(role)
    gate = Barrier(3)
    outcomes = []
    approved = req(item, "approval-concurrent")
    assert issue_approval(approved) == 1

    def worker(ref):
        gate.wait(timeout=8)
        try:
            result = PostgresIamDeadAckRecovery(RECOVERY).redrive(
                approved, actor_id="investigator", approver_id="checker"
            )
            outcomes.append(result)
        except psycopg.errors.InsufficientPrivilege:
            outcomes.append("DENIED")

    threads = [Thread(target=worker, args=(f"approval-{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    gate.wait(timeout=8)
    for thread in threads:
        thread.join(timeout=12)
        assert not thread.is_alive()
    assert sorted(str(value) for value in outcomes) == ["1", "DENIED"]
    assert read_state(item.event_id)[2] == 1


def test_stolen_recovery_credential_cannot_redrive_without_separate_grant(request):
    role, _ = request.getfixturevalue("account")
    item = make_dead(role)
    attack = req(item, f"forged-{uuid4()}")
    with psycopg.connect(RECOVERY) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT company_configuration.cp_redrive_dead_iam_ack("
                "%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    attack.event_id, attack.request_id, attack.tenant_id,
                    "attacker", "forged-reviewer", attack.approval_reference,
                    attack.reason_code, attack.evidence_reference,
                ),
            )
    assert read_state(item.event_id) == ("DEAD", 5, 0, "HTTP_REJECTED")
    with psycopg.connect(RECOVERY) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT company_configuration.cp_grant_iam_ack_redrive("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    attack.event_id, attack.request_id, attack.tenant_id,
                    "attacker", "forged-reviewer", attack.approval_reference,
                    attack.reason_code, attack.evidence_reference,
                    datetime.now(UTC) + timedelta(minutes=2),
                ),
            )


def test_approval_writer_cannot_redrive_and_grant_is_exact_scope(request):
    role, _ = request.getfixturevalue("account")
    item = make_dead(role)
    approved = req(item)
    assert issue_approval(approved) == 1
    with psycopg.connect(APPROVAL_WRITER) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT company_configuration.cp_redrive_dead_iam_ack("
                "%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    approved.event_id, approved.request_id, approved.tenant_id,
                    "investigator", "checker", approved.approval_reference,
                    approved.reason_code, approved.evidence_reference,
                ),
            )
    recovery = PostgresIamDeadAckRecovery(RECOVERY)
    for bad_actor, bad_checker, bad_reason in (
        ("attacker", "checker", approved.reason_code),
        ("investigator", "forged-checker", approved.reason_code),
        ("investigator", "checker", "INCIDENT_REVIEWED"),
    ):
        tampered = RedriveRequest(
            approved.event_id, approved.request_id, approved.tenant_id,
            approved.approval_reference, approved.evidence_reference, bad_reason,
        )
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            recovery.redrive(
                tampered, actor_id=bad_actor, approver_id=bad_checker
            )
    assert read_state(item.event_id) == ("DEAD", 5, 0, "HTTP_REJECTED")
    assert recovery.redrive(
        approved, actor_id="investigator", approver_id="checker"
    ) == 1
    with psycopg.connect(ADMIN) as conn:
        consumed = conn.execute(
            "SELECT approval_reference,redrive_number FROM "
            "company_configuration.privileged_iam_ack_recovery_consumptions "
            "WHERE event_id=%s", (item.event_id,),
        ).fetchone()
        assert consumed == (approved.approval_reference, 1)
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "DELETE FROM company_configuration.privileged_iam_ack_recovery_grants "
                "WHERE approval_reference=%s", (approved.approval_reference,),
            )


def test_grant_rejects_unbounded_ttl_and_duplicate_issuance(request):
    role, _ = request.getfixturevalue("account")
    item = make_dead(role)
    approved = req(item)
    with psycopg.connect(APPROVAL_WRITER) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT company_configuration.cp_grant_iam_ack_redrive("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    approved.event_id, approved.request_id, approved.tenant_id,
                    "investigator", "checker", approved.approval_reference,
                    approved.reason_code, approved.evidence_reference,
                    datetime.now(UTC) + timedelta(days=1),
                ),
            )
    assert issue_approval(approved) == 1
    with pytest.raises(psycopg.errors.UniqueViolation):
        issue_approval(approved)
    assert read_state(item.event_id) == ("DEAD", 5, 0, "HTTP_REJECTED")
