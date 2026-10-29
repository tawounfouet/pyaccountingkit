"""Real PostgreSQL 16 proof: signed recovery vs an independent SQL capability."""
# ruff: noqa: E402

import base64
import json
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

psycopg = pytest.importorskip("psycopg")
from test_delegated_control_plane_postgres import account  # noqa: F401

from pyaccountingkit.company_configuration.application.iam_ack_recovery import (
    IamAckRecoveryService,
    RedriveRequest,
)
from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedAccessDenied,
    VerifiedOperator,
)
from pyaccountingkit.company_configuration.infrastructure.iam.revocation import (
    VerifiedIamRevocation,
)
from pyaccountingkit.company_configuration.infrastructure.iam.signed_evidence import (
    PinnedSignedEvidenceVerifier,
    SignedEvidenceTrust,
    SignedOperatorIdentity,
)
from pyaccountingkit.company_configuration.infrastructure.iam.signed_recovery import (
    SignedRecoveryApprovalVerifier,
    require_recovery_sql_capabilities,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.iam_ack_operations import (
    PostgresIamAckApprovalGrants,
    PostgresIamDeadAckRecovery,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.iam_revocation import (
    PostgresIamRevocationRepository,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.restricted_control_plane import (
    PrivilegedCompositionDenied,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RECOVERY = os.getenv("CC_PG_IAM_RECOVERY_DSN")
IAM = os.getenv("CC_PG_IAM_REVOCATION_DSN")
DELIVERY = os.getenv("CC_PG_IAM_DELIVERY_DSN")
APPROVAL_WRITER = os.getenv("CC_PG_IAM_APPROVAL_WRITER_DSN")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, RECOVERY, IAM, DELIVERY, APPROVAL_WRITER)),
    reason="Dedicated SQL recovery and IAM revocation DSNs required",
)


def _signed(key, claims):
    def enc(x):
        data = json.dumps(x, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    header = enc({"alg": "EdDSA", "typ": "JWT", "kid": "k1"})
    payload = enc(claims)
    data = f"{header}.{payload}"
    signature = base64.urlsafe_b64encode(key.sign(data.encode())).decode().rstrip("=")
    return f"{data}.{signature}"


def _trust(key, kind, issuer):
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return SignedEvidenceTrust(issuer, "cc-iam-recovery", {"k1": public}, kind)


class Source:
    def __init__(self, token):
        self.token = token

    def read(self, reference):
        return self.token


class Clock:
    def now(self):
        return datetime.now(UTC)


class Policy:
    def require(self, *, actor, tenant_id, action):
        if (
            actor.actor_id != "investigator" or actor.tenant_id != tenant_id
            or action != "redrive_iam_ack_dead"
        ):
            raise PrivilegedAccessDenied("Current grant revoked")


@pytest.fixture
def dead_row(request):
    role, _ = request.getfixturevalue("account")
    event = VerifiedIamRevocation(
        uuid4(), uuid4(), "tenant-a", role, "rotate", "issuer", "kid", "revoker",
        "a" * 64,
    )
    assert PostgresIamRevocationRepository(IAM).apply(event) == "TOMBSTONED"
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE company_configuration.privileged_iam_ack_outbox "
            "SET state='DEAD', attempts=5,error_code='HTTP_REJECTED' WHERE event_id=%s",
            (event.event_id,),
        )
    yield event
    # Only CI owner test cleanup; never a production re-drive procedure.
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE company_configuration.privileged_iam_ack_outbox "
            "SET state='DELIVERED', lease_token=NULL,lease_until=NULL, "
            "delivered_at=clock_timestamp(),error_code=NULL WHERE event_id=%s",
            (event.event_id,),
        )


def _service(row, *, signer=None):
    operator = Ed25519PrivateKey.generate()
    reviewer = Ed25519PrivateKey.generate()
    now = int(datetime.now(UTC).timestamp())
    common = {
        "aud": "cc-iam-recovery", "iat": now - 10, "nbf": now - 10,
        "exp": now + 180, "jti": str(uuid4()), "tenant_id": "tenant-a",
    }
    actor_claims = common | {
        "iss": "https://operators.example.test", "kind": "operator", "sub": "investigator",
    }
    req = RedriveRequest(
        row.event_id, row.request_id, row.tenant_id,
        f"unique-check-{uuid4()}", "incident-evidence", "PROVIDER_RECOVERED",
    )
    approval_claims = common | {
        "iss": "https://reviewers.example.test", "kind": "recovery_approval",
        "sub": "checker", "approval_id": req.approval_reference,
        "event_id": str(row.event_id), "request_id": str(row.request_id),
        "evidence_reference": req.evidence_reference,
        "reason_code": req.reason_code,
        "issued_at": now - 5, "expires_at": now + 120,
    }
    proof = _signed(signer or reviewer, approval_claims)
    reviewer_verifier = SignedRecoveryApprovalVerifier(
        PinnedSignedEvidenceVerifier(
            _trust(reviewer, "recovery_approval", "https://reviewers.example.test")
        ),
        Source(proof),
    )
    svc = IamAckRecoveryService(
        identity=SignedOperatorIdentity(
            PinnedSignedEvidenceVerifier(
                _trust(operator, "operator", "https://operators.example.test")
            )
        ),
        approvals=reviewer_verifier,
        policy=Policy(),
        repository=PostgresIamDeadAckRecovery(RECOVERY),
        clock=Clock(),
    )
    if signer is None:
        # CI simulates a physically separate approval-writer service. A forged
        # token cannot get a grant through the dedicated signed verifier.
        signed_approval = reviewer_verifier.resolve(reference=req.approval_reference)
        PostgresIamAckApprovalGrants(APPROVAL_WRITER).issue(
            req,
            actor=VerifiedOperator("investigator", req.tenant_id),
            approval=signed_approval,
            now=datetime.now(UTC),
        )
    return svc, req, _signed(operator, actor_claims)


def test_signed_independent_recovery_approval_commits_sql_decision(dead_row):
    svc, req, token = _service(dead_row)
    assert svc.redrive(req, auth_context=token) == 1
    with psycopg.connect(ADMIN) as conn:
        outcome = conn.execute(
            "SELECT state,redrive_count FROM company_configuration.privileged_iam_ack_outbox "
            "WHERE event_id=%s", (dead_row.event_id,),
        ).fetchone()
        evidence = conn.execute(
            "SELECT actor_id,approver_id,approval_reference "
            "FROM company_configuration.privileged_iam_ack_redrive_decisions "
            "WHERE event_id=%s", (dead_row.event_id,),
        ).fetchone()
    assert outcome == ("RETRY", 1)
    assert evidence == ("investigator", "checker", req.approval_reference)


def test_forged_recovery_approval_denied_without_sql_reactivation(dead_row):
    svc, req, token = _service(dead_row, signer=Ed25519PrivateKey.generate())
    with pytest.raises(PrivilegedAccessDenied):
        svc.redrive(req, auth_context=token)
    with psycopg.connect(ADMIN) as conn:
        outcome = conn.execute(
            "SELECT state,redrive_count FROM company_configuration.privileged_iam_ack_outbox "
            "WHERE event_id=%s", (dead_row.event_id,),
        ).fetchone()
    assert outcome == ("DEAD", 0)


def test_database_recovery_capability_rejects_delivery_or_owner_login():
    require_recovery_sql_capabilities(RECOVERY)
    for dsn in (DELIVERY, ADMIN, APPROVAL_WRITER):
        with pytest.raises(PrivilegedCompositionDenied):
            require_recovery_sql_capabilities(dsn)
