"""PostgreSQL 16 signed IAM revocation receipt, replay and race evidence."""
# ruff: noqa: E402

import base64
import json
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

psycopg = pytest.importorskip("psycopg")
from test_delegated_control_plane_postgres import account  # noqa: F401

from pyaccountingkit.company_configuration.application.fence_contract import (
    FencedRoleOperation,
    PrivilegedFencePermit,
)
from pyaccountingkit.company_configuration.infrastructure.iam.signed_evidence import (
    SignedEvidenceTrust,
)
from pyaccountingkit.company_configuration.infrastructure.postgres import (
    signed_iam_revocation,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.delegated_control_plane import (
    DelegatedPrivilegedControlPlane,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
CONTROL = os.getenv("CC_PG_CONTROL_PLANE_DSN")
REVOCATION = os.getenv("CC_PG_IAM_REVOCATION_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
pytestmark = pytest.mark.skipif(
    not (ADMIN and CONTROL and REVOCATION and RUNTIME),
    reason="Dedicated independent IAM revocation PostgreSQL login required",
)


def token(private, claims):
    def enc(value):
        return base64.urlsafe_b64encode(
            json.dumps(value, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()

    msg = enc({"alg": "EdDSA", "typ": "JWT", "kid": "iam-revoke"}) + "." + enc(claims)
    return msg + "." + base64.urlsafe_b64encode(private.sign(msg.encode())).rstrip(b"=").decode()


def signed_event(permit, *, tenant=None, approval=None, identity=None):
    key = Ed25519PrivateKey.generate()
    trust = SignedEvidenceTrust(
        "https://idp-revocation.test", "cc-privileged-revocation",
        {"iam-revoke": key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )}, "revocation",
    )
    now = int(datetime.now(UTC).timestamp())
    claims = {
        "iss": "https://idp-revocation.test", "aud": "cc-privileged-revocation",
        "kind": "revocation", "sub": "iam-revocation-engine",
        "tenant_id": tenant or permit.tenant_id, "iat": now - 1,
        "nbf": now - 1, "exp": now + 180,
        "jti": str(identity or uuid4()), "request_id": str(permit.request_id),
        "login_role": permit.login_role, "operation": permit.operation,
        "approval_id": approval or permit.approval_id, "revoked_at": now - 2,
    }
    return token(key, claims), trust


def new_fence(role, operation="rotate"):
    return PrivilegedFencePermit(
        uuid4(), "tenant-a", role, operation, "operator-a", "checker-b",
        "approval-iam-event", datetime.now(UTC) + timedelta(minutes=4),
    )


def receipt_record(revocation_id):
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            "SELECT status,tenant_id,evidence_sha256 FROM "
            "company_configuration.privileged_iam_revocation_receipts "
            "WHERE revocation_id=%s", (revocation_id,),
        ).fetchone()


def test_signed_revocation_changes_active_fence_and_is_idempotent(request):
    role, _dsn = request.getfixturevalue("account")
    permit = new_fence(role)
    control = DelegatedPrivilegedControlPlane(CONTROL)
    control.issue(permit)
    event, trust = signed_event(permit)
    receiver = signed_iam_revocation.SignedIAMRevocationAcknowledger(
        dsn=REVOCATION, trust=trust,
    )
    first = receiver.apply(event)
    second = receiver.apply(event)
    assert first.status == "APPLIED" and first.enforced
    assert second == first
    assert receipt_record(first.revocation_id)[:2] == ("APPLIED", "tenant-a")
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT state FROM company_configuration.privileged_authorization_fences "
            "WHERE request_id=%s", (permit.request_id,),
        ).fetchone()[0] == "REVOKED"
        assert [r[0] for r in conn.execute(
            "SELECT action FROM company_configuration.privileged_fence_events "
            "WHERE request_id=%s ORDER BY recorded_at", (permit.request_id,),
        ).fetchall()] == ["ISSUED", "REVOKED"]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        control.execute(
            FencedRoleOperation(
                permit.request_id, permit.tenant_id, role,
                "rotate", permit.actor_id, permit.approval_id,
            ), new_password="should-not-rotate-this-role-123456",
        )


def test_revoke_after_consumption_returns_too_late_not_enforced(request):
    role, _dsn = request.getfixturevalue("account")
    control = DelegatedPrivilegedControlPlane(CONTROL)
    permit = new_fence(role)
    control.issue(permit)
    control.execute(
        FencedRoleOperation(
            permit.request_id, permit.tenant_id, role,
            "rotate", permit.actor_id, permit.approval_id,
        ), new_password="role-rotated-before-remote-revocation-123456",
    )
    event, trust = signed_event(permit)
    receipt = signed_iam_revocation.SignedIAMRevocationAcknowledger(
        dsn=REVOCATION, trust=trust,
    ).apply(event)
    assert receipt.status == "TOO_LATE" and not receipt.enforced
    assert receipt_record(receipt.revocation_id)[0] == "TOO_LATE"


def test_previous_sql_revocation_is_not_attributed_to_new_iam_event(request):
    role, _dsn = request.getfixturevalue("account")
    control = DelegatedPrivilegedControlPlane(CONTROL)
    permit = new_fence(role)
    control.issue(permit)
    assert control.revoke(
        request_id=permit.request_id, tenant_id="tenant-a", revoked_by="earlier-event",
    )
    event, trust = signed_event(permit)
    receipt = signed_iam_revocation.SignedIAMRevocationAcknowledger(
        dsn=REVOCATION, trust=trust,
    ).apply(event)
    assert receipt.status == "ALREADY_REVOKED" and not receipt.enforced


def test_signed_wrong_tenant_or_approval_is_rejected_in_sql(request):
    role, _dsn = request.getfixturevalue("account")
    control = DelegatedPrivilegedControlPlane(CONTROL)
    permit = new_fence(role)
    control.issue(permit)
    for foreign in ({"tenant": "tenant-b"}, {"approval": "other-approval"}):
        event, trust = signed_event(permit, **foreign)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            signed_iam_revocation.SignedIAMRevocationAcknowledger(
                dsn=REVOCATION, trust=trust,
            ).apply(event)
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT state FROM company_configuration.privileged_authorization_fences "
            "WHERE request_id=%s", (permit.request_id,),
        ).fetchone()[0] == "ACTIVE"


def test_role_permissions_are_separate_and_receipt_is_owner_only(request):
    role, _dsn = request.getfixturevalue("account")
    permit = new_fence(role)
    with psycopg.connect(REVOCATION) as conn:
        assert conn.execute("SELECT session_user").fetchone()[0] == "cc_iam_revocation"
        row = conn.execute(
            "SELECT rolsuper,rolcreaterole,rolbypassrls "
            "FROM pg_roles WHERE rolname=session_user"
        ).fetchone()
        assert row == (False, False, False)
    for dsn in (REVOCATION, CONTROL, RUNTIME):
        with psycopg.connect(dsn) as conn:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(
                    "SELECT * FROM company_configuration.privileged_iam_revocation_receipts"
                )
    with psycopg.connect(CONTROL) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT company_configuration.cp_ack_iam_revocation("
                "%s,%s,%s,%s,%s,%s,%s,%s)",
                (uuid4(), permit.request_id, "tenant-a", role, "rotate",
                 permit.approval_id, "revoker", "a" * 64),
            )
    with psycopg.connect(REVOCATION) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT company_configuration.cp_execute_fence("
                "%s,%s,%s,%s,%s,%s,%s)",
                (permit.request_id, "tenant-a", role, "rotate", "actor", "approval", None),
            )
