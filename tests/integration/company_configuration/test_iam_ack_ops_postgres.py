"""Real PostgreSQL proof: restricted metrics and approved DEAD-letter re-drive."""
# ruff: noqa: E402

import os
from threading import Barrier, Thread
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from test_delegated_control_plane_postgres import account  # noqa: F401

from pyaccountingkit.company_configuration.application.iam_ack_recovery import (
    RedriveRequest,
)
from pyaccountingkit.company_configuration.infrastructure.iam.revocation import (
    VerifiedIamRevocation,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.iam_ack_operations import (
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
RUNTIME = os.getenv("CC_PG_DSN")
CONTROL = os.getenv("CC_PG_CONTROL_PLANE_DSN")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, IAM, DELIVERY, RECOVERY, RUNTIME, CONTROL)),
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


def test_recovery_reactivates_dead_with_append_only_decision(request):
    role, _ = request.getfixturevalue("account")
    item = make_dead(role)
    repo = PostgresIamDeadAckRecovery(RECOVERY)
    assert any(row.event_id == item.event_id for row in repo.list_dead("tenant-a", 20))
    assert repo.list_dead("tenant-b", 20) == ()
    assert repo.redrive(req(item), actor_id="investigator", approver_id="checker") == 1
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
    assert repo.redrive(req(item), actor_id="operator", approver_id="checker") == 1
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        repo.redrive(req(item), actor_id="operator", approver_id="checker")


def test_recovery_requires_new_approval_and_has_two_redrive_limit(request):
    role, _ = request.getfixturevalue("account")
    item = make_dead(role)
    repo = PostgresIamDeadAckRecovery(RECOVERY)
    original = req(item)
    assert repo.redrive(original, actor_id="operator", approver_id="checker") == 1
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE company_configuration.privileged_iam_ack_outbox SET "
            "state='DEAD', attempts=5, error_code='HTTP_REJECTED' WHERE event_id=%s",
            (item.event_id,),
        )
    with pytest.raises(psycopg.errors.UniqueViolation):
        repo.redrive(original, actor_id="operator", approver_id="checker")
    assert repo.redrive(
        req(item), actor_id="operator", approver_id="checker"
    ) == 2
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

    def worker(ref):
        gate.wait(timeout=8)
        try:
            result = PostgresIamDeadAckRecovery(RECOVERY).redrive(
                req(item, ref), actor_id="investigator", approver_id="checker"
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
