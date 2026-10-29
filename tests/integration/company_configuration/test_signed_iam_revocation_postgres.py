"""PostgreSQL proof: signed revocations are acknowledged before remote ACK."""
# ruff: noqa: E402

import base64
import json
import os
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
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
from pyaccountingkit.company_configuration.infrastructure.iam.revocation import (
    SignedIamRevocationProcessor,
)
from pyaccountingkit.company_configuration.infrastructure.iam.signed_evidence import (
    PinnedSignedEvidenceVerifier,
    SignedEvidenceTrust,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.delegated_control_plane import (
    DelegatedPrivilegedControlPlane,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.iam_revocation import (
    PostgresIamRevocationRepository,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
CONTROL = os.getenv("CC_PG_CONTROL_PLANE_DSN")
IAM = os.getenv("CC_PG_IAM_REVOCATION_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
AUDIT = os.getenv("CC_PG_PRIVILEGED_AUDIT_DSN")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, CONTROL, IAM, RUNTIME, AUDIT)),
    reason="Dedicated PostgreSQL control-plane/IAM DB roles required",
)


class Source:
    def __init__(self, token):
        self.token = token
        self.receipts = []

    def read(self, reference):
        return self.token

    def acknowledge(self, receipt):
        self.receipts.append(receipt)


def _signed(private, claims):
    def enc(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    text = enc({"alg": "EdDSA", "typ": "JWT", "kid": "ci-revocation"})
    text += "." + enc(claims)
    return text + "." + base64.urlsafe_b64encode(
        private.sign(text.encode())
    ).rstrip(b"=").decode()


def pipeline(role, request_id, *, tenant="tenant-a", op="rotate"):
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    event = uuid4()
    now = int(datetime.now(UTC).timestamp())
    claims = {
        "iss": "https://revocations.example.test", "aud": "cc-privileged",
        "kind": "revocation", "sub": "iam-security", "tenant_id": tenant,
        "iat": now - 4, "nbf": now - 4, "exp": now + 120,
        "jti": str(event), "request_id": str(request_id),
        "login_role": role, "operation": op,
    }
    trust = SignedEvidenceTrust(
        "https://revocations.example.test", "cc-privileged",
        {"ci-revocation": public}, "revocation",
    )
    src = Source(_signed(key, claims))
    svc = SignedIamRevocationProcessor(
        verifier=PinnedSignedEvidenceVerifier(trust), source=src,
        repository=PostgresIamRevocationRepository(IAM),
    )
    return svc, src, event


def permit(role, request_id=None):
    return PrivilegedFencePermit(
        request_id or uuid4(), "tenant-a", role, "rotate", "operator-a",
        "checker-b", "approval-one", datetime.now(UTC) + timedelta(minutes=5),
    )


def run(fence):
    return FencedRoleOperation(
        fence.request_id, fence.tenant_id, fence.login_role, fence.operation,
        fence.actor_id, fence.approval_id,
    )


def _receipt_count(request_id):
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            "SELECT count(*) FROM company_configuration.privileged_iam_revocation_receipts "
            "WHERE request_id=%s", (request_id,),
        ).fetchone()[0]


def test_signed_revoke_before_issuance_blocks_future_sql_fence(request):
    role, _ = request.getfixturevalue("account")
    fence = permit(role)
    service, src, event = pipeline(role, fence.request_id)
    receipt = service.process(event)
    assert receipt.disposition == "TOMBSTONED"
    assert src.receipts == [receipt]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        DelegatedPrivilegedControlPlane(CONTROL).issue(fence)
    assert _receipt_count(fence.request_id) == 1


def test_signed_revoke_existing_active_fence_and_idempotent_retry(request):
    role, _ = request.getfixturevalue("account")
    fence = permit(role)
    control = DelegatedPrivilegedControlPlane(CONTROL)
    control.issue(fence)
    service, src, event = pipeline(role, fence.request_id)
    assert service.process(event).disposition == "REVOKED"
    assert service.process(event).disposition == "REVOKED"
    assert len(src.receipts) == 2 and _receipt_count(fence.request_id) == 1
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        control.execute(run(fence), new_password="revoked-test-password-strong-123")
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT state FROM company_configuration.privileged_authorization_fences "
            "WHERE request_id=%s", (fence.request_id,),
        ).fetchone()[0] == "REVOKED"
        assert [row[0] for row in conn.execute(
            "SELECT action FROM company_configuration.privileged_fence_events "
            "WHERE request_id=%s ORDER BY recorded_at", (fence.request_id,),
        ).fetchall()] == ["ISSUED", "REVOKED"]


def test_ack_after_sql_ddl_is_explicitly_not_successful_prevention(request):
    role, _ = request.getfixturevalue("account")
    fence = permit(role)
    control = DelegatedPrivilegedControlPlane(CONTROL)
    control.issue(fence)
    control.execute(run(fence), new_password="preexisting-commit-password-123456")
    service, src, event = pipeline(role, fence.request_id)
    outcome = service.process(event)
    assert outcome.disposition == "ALREADY_CONSUMED"
    assert src.receipts == [outcome]
    assert _receipt_count(fence.request_id) == 1


@pytest.mark.parametrize("change", ["tenant", "role", "operation"])
def test_signed_scope_mismatch_not_acknowledged(request, change):
    role, _ = request.getfixturevalue("account")
    fence = permit(role)
    DelegatedPrivilegedControlPlane(CONTROL).issue(fence)
    kwargs = {}
    if change == "tenant":
        kwargs["tenant"] = "tenant-b"
    elif change == "role":
        role = "cc_runtime_different_registered"
    else:
        kwargs["op"] = "revoke"
    service, source, event = pipeline(role, fence.request_id, **kwargs)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        service.process(event)
    assert not source.receipts and _receipt_count(fence.request_id) == 0


def test_only_iam_receiver_can_call_sql_ack_endpoint(request):
    role, _ = request.getfixturevalue("account")
    args = (uuid4(), uuid4(), "tenant-a", role, "rotate", "issuer", "kid", "iam", "0" * 64)
    for dsn in (RUNTIME, CONTROL, AUDIT):
        with psycopg.connect(dsn) as conn:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(
                    "SELECT company_configuration.cp_ack_iam_revocation("
                    "%s,%s,%s,%s,%s,%s,%s,%s,%s)", args,
                )
    with psycopg.connect(IAM) as conn:
        assert conn.execute(
            "SELECT session_user,rolsuper,rolcreaterole,rolbypassrls "
            "FROM pg_roles WHERE rolname=session_user"
        ).fetchone() == ("cc_iam_revocation", False, False, False)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT * FROM company_configuration.privileged_iam_revocation_receipts"
            )
    with psycopg.connect(IAM) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "SELECT company_configuration.cp_revoke_fence(%s,%s,%s)",
                (uuid4(), "tenant-a", "iam"),
            )


def test_tombstone_and_issue_are_serialized_before_commit(request):
    role, _ = request.getfixturevalue("account")
    fence = permit(role)
    control = DelegatedPrivilegedControlPlane(CONTROL)
    ready, finished = Event(), Event()
    errors = []

    def issue_worker():
        ready.set()
        try:
            control.issue(fence)
        except psycopg.errors.InsufficientPrivilege:
            errors.append("DENIED")
        finally:
            finished.set()

    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 77011))",
            (str(fence.request_id),),
        )
        worker = Thread(target=issue_worker)
        worker.start()
        assert ready.wait(timeout=5)
        assert not finished.wait(timeout=0.1)
        conn.execute(
            "INSERT INTO company_configuration.privileged_iam_revocation_receipts "
            "(request_id,event_id,tenant_id,login_role,operation,issuer,signer_kid,"
            "revoker_id,signed_digest,disposition) "
            "VALUES (%s,%s,%s,%s,'rotate','iam','kid','iam',%s,'TOMBSTONED')",
            (fence.request_id, uuid4(), "tenant-a", role, "0" * 64),
        )
    worker.join(timeout=10)
    assert not worker.is_alive() and errors == ["DENIED"]
    assert _receipt_count(fence.request_id) == 1
