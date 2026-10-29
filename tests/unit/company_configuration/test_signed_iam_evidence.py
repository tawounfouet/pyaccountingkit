"""Cryptographic negative tests for the L02-07i pinned-key port adapters."""

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
    PinnedSignedEvidenceVerifier,
    SignedApprovalVerifier,
    SignedEvidenceTrust,
    SignedOperatorIdentity,
)


def b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def signed(private, claims, header=None, payload_bytes=None):
    h = header if header is not None else {"alg": "EdDSA", "typ": "JWT", "kid": "kid1"}
    h64 = b64(json.dumps(h, separators=(",", ":")).encode())
    p64 = b64(payload_bytes if payload_bytes is not None else json.dumps(claims).encode())
    message = (h64 + "." + p64).encode()
    return message.decode() + "." + b64(private.sign(message))


@pytest.fixture
def evidence():
    operator_key = Ed25519PrivateKey.generate()
    approval_key = Ed25519PrivateKey.generate()
    def raw(key):
        return key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
    operator_trust = SignedEvidenceTrust(
        "https://idp.example.test", "cc-privileged", {"kid1": raw(operator_key)},
        "operator",
    )
    approval_trust = SignedEvidenceTrust(
        "https://approvals.example.test", "cc-privileged", {"kid1": raw(approval_key)},
        "approval",
    )
    now = int(datetime.now(UTC).timestamp())
    shared = {
        "aud": "cc-privileged", "tenant_id": "tenant-a", "iat": now - 10,
        "nbf": now - 10, "exp": now + 180, "jti": str(uuid4()),
    }
    operator_claims = shared | {
        "iss": "https://idp.example.test", "kind": "operator", "sub": "operator-a",
    }
    approval_claims = shared | {
        "iss": "https://approvals.example.test", "kind": "approval", "sub": "reviewer-b",
        "approval_id": "approval-123", "request_id": str(uuid4()),
        "login_role": "cc_runtime_tenant_a", "operation": "rotate",
        "issued_at": now - 5, "expires_at": now + 120,
    }
    return (
        operator_key, approval_key, operator_trust, approval_trust,
        operator_claims, approval_claims,
    )


class Source:
    def __init__(self, token, fail=False):
        self.token = token
        self.fail = fail

    def read(self, reference):
        if self.fail:
            raise ConnectionError("offline")
        return self.token


def test_pinned_operator_signature_returns_authenticated_identity(evidence):
    key, _, trust, _, claims, _ = evidence
    port = SignedOperatorIdentity(PinnedSignedEvidenceVerifier(trust))
    operator = port.verify(signed(key, claims))
    assert (operator.actor_id, operator.tenant_id) == ("operator-a", "tenant-a")


def test_pinned_independent_approval_maps_exact_request_and_checker(evidence):
    _, key, _, trust, _, claims = evidence
    port = SignedApprovalVerifier(PinnedSignedEvidenceVerifier(trust), Source(signed(key, claims)))
    approval = port.resolve(reference="approval-123")
    assert (approval.approver_id, approval.tenant_id) == ("reviewer-b", "tenant-a")
    assert approval.request_id.hex == claims["request_id"].replace("-", "")
    assert approval.issued_at.tzinfo == UTC


@pytest.mark.parametrize("mutation", [
    {"aud": "other-app"}, {"iss": "https://attacker.example.test"},
    {"kind": "approval"}, {"tenant_id": ""}, {"jti": "not-uuid"},
    {"exp": 9999999999}, {"iat": 9999999999}, {"nbf": 9999999999},
    {"iat": "yesterday"}, {"exp": True},
])
def test_wrong_claims_fail_closed(evidence, mutation):
    key, _, trust, _, claims, _ = evidence
    with pytest.raises(PrivilegedAccessDenied):
        PinnedSignedEvidenceVerifier(trust).verify(signed(key, claims | mutation))


@pytest.mark.parametrize("header", [
    {"alg": "none", "typ": "JWT", "kid": "kid1"},
    {"alg": "HS256", "typ": "JWT", "kid": "kid1"},
    {"alg": "EdDSA", "typ": "JWT", "kid": "untrusted"},
    {"alg": "EdDSA", "typ": "JWT", "kid": "kid1", "jwk": {}},
    {"alg": "EdDSA", "typ": "not-JWT", "kid": "kid1"},
])
def test_algorithm_key_or_header_substitution_rejected(evidence, header):
    key, _, trust, _, claims, _ = evidence
    with pytest.raises(PrivilegedAccessDenied):
        PinnedSignedEvidenceVerifier(trust).verify(signed(key, claims, header=header))


def test_payload_tampering_and_untrusted_signature_are_rejected(evidence):
    key, other, trust, _, claims, _ = evidence
    good = signed(key, claims)
    payload = good.split(".")[1]
    forged = b64(json.dumps(claims | {"sub": "attacker"}).encode())
    with pytest.raises(PrivilegedAccessDenied):
        PinnedSignedEvidenceVerifier(trust).verify(good.replace(payload, forged))
    with pytest.raises(PrivilegedAccessDenied):
        PinnedSignedEvidenceVerifier(trust).verify(signed(other, claims))


def test_duplicate_signed_json_claim_and_noncanonical_encoding_rejected(evidence):
    key, _, trust, _, claims, _ = evidence
    raw = json.dumps(claims).encode()
    payload = raw[:-1] + b',"sub":"override"}'
    with pytest.raises(PrivilegedAccessDenied):
        PinnedSignedEvidenceVerifier(trust).verify(signed(key, claims, payload_bytes=payload))
    with pytest.raises(PrivilegedAccessDenied):
        PinnedSignedEvidenceVerifier(trust).verify("bad.token.encoding=bad")


def test_approval_mismatched_reference_or_source_failure_denied(evidence):
    _, key, _, trust, _, claims = evidence
    verifier = PinnedSignedEvidenceVerifier(trust)
    reader = SignedApprovalVerifier(verifier, Source(signed(key, claims)))
    with pytest.raises(PrivilegedAccessDenied):
        reader.resolve(reference="approval-substituted")
    with pytest.raises(PrivilegedAccessDenied):
        SignedApprovalVerifier(verifier, Source("", fail=True)).resolve(
            reference="approval-123"
        )


def test_wrong_evidence_kind_and_wrong_approval_trust_root_rejected(evidence):
    operator_key, approval_key, op_trust, ap_trust, op_claims, ap_claims = evidence
    with pytest.raises(ValueError):
        SignedOperatorIdentity(PinnedSignedEvidenceVerifier(ap_trust))
    with pytest.raises(ValueError):
        SignedApprovalVerifier(PinnedSignedEvidenceVerifier(op_trust), Source(""))
    with pytest.raises(PrivilegedAccessDenied):
        PinnedSignedEvidenceVerifier(ap_trust).verify(signed(operator_key, op_claims))
    with pytest.raises(PrivilegedAccessDenied):
        PinnedSignedEvidenceVerifier(op_trust).verify(signed(approval_key, ap_claims))


def test_approval_expiry_exceeding_signed_envelope_denied(evidence):
    _, key, _, trust, _, claims = evidence
    bad = claims | {"expires_at": claims["exp"] + 1}
    port = SignedApprovalVerifier(PinnedSignedEvidenceVerifier(trust), Source(signed(key, bad)))
    with pytest.raises(PrivilegedAccessDenied):
        port.resolve(reference="approval-123")


def test_pinned_key_input_validation(evidence):
    with pytest.raises(ValueError):
        SignedEvidenceTrust("issuer", "aud", {"kid1": b"bad"}, "operator")
    with pytest.raises(ValueError):
        SignedEvidenceTrust("issuer", "aud", {}, "operator")
