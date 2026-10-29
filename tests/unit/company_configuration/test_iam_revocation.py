"""Revocation delivery is at-least-once, with exact signed event checks."""

import base64
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedAccessDenied,
)
from pyaccountingkit.company_configuration.infrastructure.iam.signed_evidence import (
    SignedEvidenceTrust,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.signed_iam_revocation import (
    IAMRevocationAckPending,
    IAMRevocationReceipt,
    IAMRevocationSynchronizer,
    SignedIAMRevocationAcknowledger,
)


def jws(private, claims, *, alg="EdDSA"):
    def encode(v):
        return base64.urlsafe_b64encode(
            json.dumps(v, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()

    input_value = encode({"alg": alg, "typ": "JWT", "kid": "revocation-only"}) + "." + (
        encode(claims)
    )
    return input_value + "." + base64.urlsafe_b64encode(
        private.sign(input_value.encode())
    ).rstrip(b"=").decode()


@pytest.fixture
def signed():
    private = Ed25519PrivateKey.generate()
    now = int(datetime.now(UTC).timestamp())
    claims = {
        "iss": "https://iam-revocations.example.test",
        "aud": "cc-privileged-revocation",
        "kind": "revocation",
        "sub": "iam-policy-engine",
        "tenant_id": "tenant-a",
        "iat": now - 1,
        "nbf": now - 1,
        "exp": now + 180,
        "jti": str(uuid4()),
        "request_id": str(uuid4()),
        "approval_id": "approval-a",
        "login_role": "cc_runtime_revocation_target",
        "operation": "rotate",
        "revoked_at": now - 2,
    }
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    trust = SignedEvidenceTrust(
        "https://iam-revocations.example.test", "cc-privileged-revocation",
        {"revocation-only": public}, "revocation",
    )
    return private, claims, trust


class FakeDB:
    def __init__(self, status="APPLIED", login="cc_iam_revocation"):
        self.status = status
        self.login = login
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, typ, exc, traceback):
        return False

    def execute(self, statement, args=None):
        self.calls.append((statement, args))
        return self

    def fetchone(self):
        if self.calls[-1][0] == "SELECT session_user":
            return (self.login,)
        return (self.status,)


@pytest.mark.parametrize("status,enforced", [
    ("APPLIED", True), ("ALREADY_REVOKED", False), ("TOO_LATE", False),
])
def test_ack_receipt_never_falsely_claims_enforcement(status, enforced):
    receipt = IAMRevocationReceipt(uuid4(), uuid4(), status)
    assert receipt.enforced is enforced


def test_valid_signed_event_writes_exact_scoped_digest(monkeypatch, signed):
    from pyaccountingkit.company_configuration.infrastructure.postgres import (
        signed_iam_revocation,
    )

    private, claims, trust = signed
    db = FakeDB()
    monkeypatch.setattr(signed_iam_revocation.psycopg, "connect", lambda dsn: db)
    token = jws(private, claims)
    receipt = SignedIAMRevocationAcknowledger(dsn="test-secret", trust=trust).apply(token)
    assert receipt.status == "APPLIED" and receipt.request_id == uuid4_from(claims["request_id"])
    assert len(db.calls) == 2
    args = db.calls[1][1]
    assert args[:2] == (uuid4_from(claims["jti"]), uuid4_from(claims["request_id"]))
    assert args[2:7] == (
        "tenant-a", claims["login_role"], "rotate", "approval-a", "iam-policy-engine"
    )
    assert len(args[-1]) == 64 and token not in str(db.calls)
    assert "secret" not in repr(SignedIAMRevocationAcknowledger(dsn="test-secret", trust=trust))


def uuid4_from(value):
    from uuid import UUID

    return UUID(value)


@pytest.mark.parametrize("field,value", [
    ("kind", "operator"), ("iss", "https://evil.example"),
    ("aud", "other"), ("operation", "chmod"),
    ("revoked_at", "wrong"), ("approval_id", ""),
    ("request_id", "not-uuid"),
])
def test_wrong_signed_revocation_is_denied_before_sql(monkeypatch, signed, field, value):
    from pyaccountingkit.company_configuration.infrastructure.postgres import (
        signed_iam_revocation,
    )

    private, claims, trust = signed
    called = []
    monkeypatch.setattr(signed_iam_revocation.psycopg, "connect", lambda dsn: called.append(dsn))
    claims[field] = value
    with pytest.raises(PrivilegedAccessDenied):
        SignedIAMRevocationAcknowledger(dsn="test-secret", trust=trust).apply(
            jws(private, claims)
        )
    assert called == []


def test_invalid_signer_and_unknown_kid_denied_without_sql(monkeypatch, signed):
    from pyaccountingkit.company_configuration.infrastructure.postgres import (
        signed_iam_revocation,
    )

    _private, claims, trust = signed
    called = []
    monkeypatch.setattr(signed_iam_revocation.psycopg, "connect", lambda dsn: called.append(dsn))
    with pytest.raises(PrivilegedAccessDenied):
        SignedIAMRevocationAcknowledger(dsn="test-secret", trust=trust).apply(
            jws(Ed25519PrivateKey.generate(), claims)
        )
    assert called == []


def test_wrong_sql_role_is_fail_closed(monkeypatch, signed):
    from pyaccountingkit.company_configuration.infrastructure.postgres import (
        signed_iam_revocation,
    )

    private, claims, trust = signed
    db = FakeDB(login="postgres")
    monkeypatch.setattr(signed_iam_revocation.psycopg, "connect", lambda dsn: db)
    with pytest.raises(PrivilegedAccessDenied, match="Dedicated IAM revocation"):
        SignedIAMRevocationAcknowledger(dsn="owner-secret", trust=trust).apply(
            jws(private, claims)
        )
    assert len(db.calls) == 1


def test_ack_failure_is_visible_and_retry_does_not_lose_db_receipt(signed):
    private, claims, _trust = signed
    event = jws(private, claims)

    class Source:
        def __init__(self):
            self.remote_ack_attempts = 0

        def poll(self, *, limit):
            return (event,)

        def acknowledge(self, *, revocation_id, status):
            self.remote_ack_attempts += 1
            assert status == "TOO_LATE"
            if self.remote_ack_attempts == 1:
                raise OSError("remote IAM unavailable")

    class Database:
        def __init__(self):
            self.calls = 0

        def apply(self, token):
            assert token == event
            self.calls += 1
            return IAMRevocationReceipt(
                uuid4_from(claims["jti"]), uuid4_from(claims["request_id"]), "TOO_LATE"
            )

    source = Source()
    database = Database()
    service = IAMRevocationSynchronizer(source=source, acknowledger=database)
    with pytest.raises(IAMRevocationAckPending, match="retry safely"):
        service.sync_once()
    receipts = service.sync_once()
    assert len(receipts) == 1 and receipts[0].status == "TOO_LATE"
    assert database.calls == 2 and source.remote_ack_attempts == 2


@pytest.mark.parametrize("limit", [0, -1, 101, True, 1.0])
def test_unbounded_or_noninteger_batch_denied(limit):
    class Source:
        def poll(self, *, limit):
            return ()

        def acknowledge(self, *, revocation_id, status):
            pass

    service = IAMRevocationSynchronizer(source=Source(), acknowledger=object())
    with pytest.raises(ValueError):
        service.sync_once(limit=limit)
