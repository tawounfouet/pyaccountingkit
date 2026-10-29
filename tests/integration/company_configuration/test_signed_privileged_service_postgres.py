"""Real PostgreSQL: signed IAM evidence through restricted audit + role fencing."""
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

from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedAccessDenied,
    PrivilegedRoleRequest,
)
from pyaccountingkit.company_configuration.infrastructure.iam.signed_evidence import (
    PinnedSignedEvidenceVerifier,
    SignedApprovalVerifier,
    SignedEvidenceTrust,
    SignedOperatorIdentity,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.restricted_control_plane import (
    build_restricted_privileged_service,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
CONTROL = os.getenv("CC_PG_CONTROL_PLANE_DSN")
AUDIT = os.getenv("CC_PG_PRIVILEGED_AUDIT_DSN")
pytestmark = pytest.mark.skipif(
    not (ADMIN and CONTROL and AUDIT), reason="Restricted PostgreSQL roles are required"
)


def token(private, claims):
    def encoded(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()
    content = encoded({"alg": "EdDSA", "typ": "JWT", "kid": "test-key"}) + "." + encoded(
        claims
    )
    return content + "." + base64.urlsafe_b64encode(
        private.sign(content.encode())
    ).rstrip(b"=").decode()


def trusted_public(key):
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )


class Source:
    def __init__(self, value):
        self.value = value

    def read(self, reference):
        return self.value


class Policy:
    def require(self, *, principal, request):
        assert principal.actor_id == "operator-a"
        assert principal.tenant_id == request.tenant_id


class Clock:
    def now(self):
        return datetime.now(UTC)


def environment_for(role, *, wrong_approval_request=False, signer_is_wrong=False):
    request = PrivilegedRoleRequest(
        uuid4(), "tenant-a", role, "rotate", "approval-signed-123",
        "signed independent approval for CI test",
    )
    operator_private = Ed25519PrivateKey.generate()
    approval_private = Ed25519PrivateKey.generate()
    now = int(datetime.now(UTC).timestamp())
    common = {
        "aud": "cc-privileged", "tenant_id": "tenant-a", "iat": now - 5,
        "nbf": now - 5, "exp": now + 240, "jti": str(uuid4()),
    }
    operator_claims = common | {
        "iss": "https://idp.example.test", "kind": "operator", "sub": "operator-a",
    }
    approval_claims = common | {
        "iss": "https://approvals.example.test", "kind": "approval",
        "sub": "checker-b", "approval_id": request.approval_reference,
        "request_id": str(uuid4() if wrong_approval_request else request.request_id),
        "login_role": role, "operation": "rotate",
        "issued_at": now - 5, "expires_at": now + 180,
    }
    operator_trust = SignedEvidenceTrust(
        "https://idp.example.test", "cc-privileged",
        {"test-key": trusted_public(operator_private)}, "operator",
    )
    approval_trust = SignedEvidenceTrust(
        "https://approvals.example.test", "cc-privileged",
        {"test-key": trusted_public(approval_private)}, "approval",
    )
    fake_private = Ed25519PrivateKey.generate()
    operator_token = token(
        fake_private if signer_is_wrong else operator_private, operator_claims
    )
    approval_source = Source(token(approval_private, approval_claims))
    service = build_restricted_privileged_service(
        audit_writer_dsn=AUDIT, control_plane_dsn=CONTROL,
        identity=SignedOperatorIdentity(PinnedSignedEvidenceVerifier(operator_trust)),
        approvals=SignedApprovalVerifier(
            PinnedSignedEvidenceVerifier(approval_trust), approval_source
        ),
        policy=Policy(), clock=Clock(),
    )
    return service, request, operator_token


def observed(request_id):
    with psycopg.connect(ADMIN) as conn:
        phases = [row[0] for row in conn.execute(
            "SELECT phase FROM company_configuration.privileged_operation_audit "
            "WHERE request_id=%s", (request_id,)
        ).fetchall()]
        fence = conn.execute(
            "SELECT state FROM company_configuration.privileged_authorization_fences "
            "WHERE request_id=%s", (request_id,)
        ).fetchone()
    return sorted(phases), fence


def test_signed_operator_and_signed_approval_execute_via_restricted_db_roles(account):
    role, _ = account
    service, request, auth = environment_for(role)
    receipt = service.execute(
        request, auth_context=auth,
        new_password="signed-e2e-new-password-strong-123",
    )
    assert receipt.operation == "rotate"
    assert observed(request.request_id) == (["INTENT", "SUCCEEDED"], ("CONSUMED",))


def test_forged_operator_signature_refuses_ddl_and_audit(account):
    role, _ = account
    service, request, auth = environment_for(role, signer_is_wrong=True)
    with pytest.raises(PrivilegedAccessDenied):
        service.execute(
            request, auth_context=auth,
            new_password="unused-signed-password-123456",
        )
    assert observed(request.request_id) == ([], None)


def test_signed_approval_with_wrong_request_cannot_issue_fence(account):
    role, _ = account
    service, request, auth = environment_for(role, wrong_approval_request=True)
    with pytest.raises(PrivilegedAccessDenied, match="APPROVAL_INVALID"):
        service.execute(
            request, auth_context=auth,
            new_password="unused-signed-password-123456",
        )
    assert observed(request.request_id) == (["DENIED"], None)
