"""Pinned, independently sourced recovery approvals: forgery and replay negatives."""

import base64
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pyaccountingkit.company_configuration.application.iam_ack_recovery import (
    IamAckRecoveryService,
    RedriveRequest,
)
from pyaccountingkit.company_configuration.application.privileged_operations import (
    PrivilegedAccessDenied,
)
from pyaccountingkit.company_configuration.infrastructure.iam.signed_evidence import (
    PinnedSignedEvidenceVerifier,
    SignedEvidenceTrust,
    SignedOperatorIdentity,
)
from pyaccountingkit.company_configuration.infrastructure.iam.signed_recovery import (
    SignedRecoveryApprovalVerifier,
    SignedRecoverySettings,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.signed_control_plane import (
    UnsafeControlPlaneDeployment,
)


def encode(value):
    if isinstance(value, bytes):
        data = value
    else:
        data = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def sign(key, claims, *, header=None):
    header = header or {"alg": "EdDSA", "typ": "JWT", "kid": "kid-recovery"}
    data = f"{encode(header)}.{encode(claims)}"
    return data + "." + encode(key.sign(data.encode("ascii")))


def public(key):
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )


class Source:
    def __init__(self, token):
        self.token = token
        self.calls = 0
        self.second = None
        self.fail = False

    def read(self, reference):
        self.calls += 1
        if self.fail:
            raise ConnectionError("approval source offline")
        return self.second if self.calls > 1 and self.second else self.token


class Policy:
    def __init__(self):
        self.calls = 0
        self.fail_after = None

    def require(self, *, actor, tenant_id, action):
        self.calls += 1
        if (
            actor.tenant_id != "tenant-a" or tenant_id != "tenant-a"
            or action != "redrive_iam_ack_dead"
            or (self.fail_after is not None and self.calls >= self.fail_after)
        ):
            raise PrivilegedAccessDenied("Current grant unavailable")


class Repo:
    def __init__(self):
        self.calls = []

    def redrive(self, request, *, actor_id, approver_id):
        self.calls.append((request, actor_id, approver_id))
        return 1


class Clock:
    def now(self):
        return datetime.now(UTC)


@pytest.fixture
def case():
    actor_key = Ed25519PrivateKey.generate()
    checker_key = Ed25519PrivateKey.generate()
    now = int(datetime.now(UTC).timestamp())
    request = RedriveRequest(
        uuid4(), uuid4(), "tenant-a", "signed-recovery-approval-001",
        "incident-immutable-evidence", "PROVIDER_RECOVERED",
    )
    base = {
        "aud": "cc-recovery", "tenant_id": request.tenant_id,
        "iat": now - 10, "nbf": now - 10, "exp": now + 180, "jti": str(uuid4()),
    }
    op_claims = base | {
        "iss": "https://operators.example.test", "kind": "operator",
        "sub": "investigator-a",
    }
    approval_claims = base | {
        "iss": "https://reviewers.example.test", "kind": "recovery_approval",
        "sub": "independent-checker-b", "approval_id": request.approval_reference,
        "event_id": str(request.event_id), "request_id": str(request.request_id),
        "evidence_reference": request.evidence_reference,
        "reason_code": request.reason_code,
        "issued_at": now - 5, "expires_at": now + 120,
    }
    actor_trust = SignedEvidenceTrust(
        "https://operators.example.test", "cc-recovery", {"kid-recovery": public(actor_key)},
        "operator",
    )
    checker_trust = SignedEvidenceTrust(
        "https://reviewers.example.test", "cc-recovery",
        {"kid-recovery": public(checker_key)}, "recovery_approval",
    )
    return actor_key, checker_key, actor_trust, checker_trust, request, op_claims, approval_claims


def build_service(case, *, signed_approval=None):
    actor_key, checker_key, actor_trust, checker_trust, request, actor, approval = case
    source = Source(signed_approval or sign(checker_key, approval))
    repo = Repo()
    policy = Policy()
    svc = IamAckRecoveryService(
        identity=SignedOperatorIdentity(PinnedSignedEvidenceVerifier(actor_trust)),
        approvals=SignedRecoveryApprovalVerifier(
            PinnedSignedEvidenceVerifier(checker_trust), source,
        ),
        repository=repo, policy=policy, clock=Clock(),
    )
    return svc, source, policy, repo, sign(actor_key, actor)


def test_signed_recovery_executes_exact_authorization_twice(case):
    svc, source, policy, repo, identity = build_service(case)
    assert svc.redrive(case[4], auth_context=identity) == 1
    assert source.calls == 2 and policy.calls == 2
    assert repo.calls[0][1:] == ("investigator-a", "independent-checker-b")


@pytest.mark.parametrize("field,value", [
    ("tenant_id", "tenant-b"), ("event_id", str(uuid4())),
    ("request_id", str(uuid4())), ("approval_id", "another"),
    ("evidence_reference", "different-evidence"),
    ("reason_code", "UNAPPROVED_REASON"),
    ("sub", "investigator-a"), ("expires_at", 1),
    ("issued_at", 1), ("exp", 9999999999),
])
def test_signed_scope_failure_denied_before_sql(case, field, value):
    actor, reviewer, _, _, _, _, claims = case
    svc, _, _, repo, identity = build_service(
        case, signed_approval=sign(reviewer, claims | {field: value}),
    )
    with pytest.raises(PrivilegedAccessDenied):
        svc.redrive(case[4], auth_context=identity)
    assert repo.calls == []


def test_signed_recovery_rejects_wrong_signer_and_algorithms(case):
    actor_key, _, _, _, _, _, claims = case
    forged = sign(actor_key, claims)
    svc, _, _, repo, identity = build_service(case, signed_approval=forged)
    with pytest.raises(PrivilegedAccessDenied):
        svc.redrive(case[4], auth_context=identity)
    assert repo.calls == []


@pytest.mark.parametrize("algorithm", ["none", "HS256", "RS256"])
def test_recovery_rejects_algorithm_substitution(case, algorithm):
    _, reviewer, _, _, _, _, claims = case
    forged = sign(
        reviewer, claims, header={"alg": algorithm, "typ": "JWT", "kid": "kid-recovery"}
    )
    svc, _, _, repo, identity = build_service(case, signed_approval=forged)
    with pytest.raises(PrivilegedAccessDenied):
        svc.redrive(case[4], auth_context=identity)
    assert repo.calls == []


def test_recovery_source_outage_fails_closed(case):
    svc, source, _, repo, identity = build_service(case)
    source.fail = True
    with pytest.raises(PrivilegedAccessDenied):
        svc.redrive(case[4], auth_context=identity)
    assert repo.calls == []


def test_recovery_approval_changed_before_sql_fails_closed(case):
    _, key, _, _, _, _, claims = case
    svc, source, _, repo, identity = build_service(case)
    source.second = sign(key, claims | {"reason_code": "INCIDENT_REVIEWED"})
    with pytest.raises(PrivilegedAccessDenied):
        svc.redrive(case[4], auth_context=identity)
    assert repo.calls == [] and source.calls == 2


def test_recovery_current_policy_revoked_before_sql_fails_closed(case):
    svc, _, policy, repo, identity = build_service(case)
    policy.fail_after = 2
    with pytest.raises(PrivilegedAccessDenied):
        svc.redrive(case[4], auth_context=identity)
    assert repo.calls == []


def test_recovery_wrong_jws_kind_rejected(case):
    _, _, op_trust, _, _, _, _ = case
    with pytest.raises(ValueError):
        SignedRecoveryApprovalVerifier(PinnedSignedEvidenceVerifier(op_trust), Source(""))


def env_for(case):
    _, _, actor_trust, reviewer_trust, _, _, _ = case
    return {
        "CC_PG_IAM_RECOVERY_DSN": (
            "postgresql://cc_iam_recovery:private@db.example.test/recovery"
            "?sslmode=verify-full"
        ),
        "CC_IAM_AUDIENCE": "cc-recovery",
        "CC_IAM_OPERATOR_ISSUER": actor_trust.issuer,
        "CC_IAM_RECOVERY_APPROVAL_ISSUER": reviewer_trust.issuer,
        "CC_IAM_OPERATOR_KID": "operator-a",
        "CC_IAM_RECOVERY_APPROVAL_KID": "reviewer-b",
        "CC_IAM_OPERATOR_ED25519_PUBLIC_B64": base64.b64encode(
            next(iter(actor_trust.keys.values()))
        ).decode(),
        "CC_IAM_RECOVERY_APPROVAL_ED25519_PUBLIC_B64": base64.b64encode(
            next(iter(reviewer_trust.keys.values()))
        ).decode(),
    }


def test_separate_pinned_recovery_settings(case):
    settings = SignedRecoverySettings.from_environment(env_for(case))
    assert settings.recovery_approval_trust.kind == "recovery_approval"
    assert "private" not in repr(settings)


@pytest.mark.parametrize("field,value", [
    ("CC_PG_IAM_RECOVERY_DSN", "postgresql://postgres:private@db.example.test/recovery"
     "?sslmode=verify-full"),
    ("CC_PG_IAM_RECOVERY_DSN", "postgresql://cc_iam_recovery:private@localhost/recovery"
     "?sslmode=disable"),
    ("CC_IAM_RECOVERY_APPROVAL_ISSUER", "https://operators.example.test"),
    ("CC_IAM_AUDIENCE", ""),
])
def test_recovery_startup_refuses_unsafe_settings(case, field, value):
    env = env_for(case) | {field: value}
    with pytest.raises(UnsafeControlPlaneDeployment):
        SignedRecoverySettings.from_environment(env)


def test_startup_refuses_shared_signer_and_admin_dsn(case):
    env = env_for(case)
    env["CC_IAM_RECOVERY_APPROVAL_ED25519_PUBLIC_B64"] = (
        env["CC_IAM_OPERATOR_ED25519_PUBLIC_B64"]
    )
    with pytest.raises(UnsafeControlPlaneDeployment):
        SignedRecoverySettings.from_environment(env)
    env = env_for(case) | {"CC_PG_ADMIN_DSN": "secret"}
    with pytest.raises(UnsafeControlPlaneDeployment):
        SignedRecoverySettings.from_environment(env)
