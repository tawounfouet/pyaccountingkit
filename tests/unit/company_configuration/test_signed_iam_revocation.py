"""L02-07j: signed IAM revocation and remote acknowledgement semantics."""

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
from pyaccountingkit.company_configuration.infrastructure.iam.revocation import (
    RemoteAcknowledgementIncomplete,
    SignedIamRevocationProcessor,
)
from pyaccountingkit.company_configuration.infrastructure.iam.signed_evidence import (
    PinnedSignedEvidenceVerifier,
    SignedEvidenceTrust,
)


def _token(key, claims):
    def enc(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()

    head = enc({"alg": "EdDSA", "typ": "JWT", "kid": "iam-revocation-1"})
    payload = enc(claims)
    raw = head + "." + payload
    return raw + "." + base64.urlsafe_b64encode(key.sign(raw.encode())).rstrip(b"=").decode()


class Source:
    def __init__(self, token):
        self.token = token
        self.acks = []
        self.fail_ack = False
        self.fail_read = False

    def read(self, event_id):
        if self.fail_read:
            raise ConnectionError("IAM offline")
        return self.token

    def acknowledge(self, receipt):
        if self.fail_ack:
            raise ConnectionError("ACK channel offline")
        self.acks.append(receipt)


class Repo:
    def __init__(self, outcome="TOMBSTONED"):
        self.outcome = outcome
        self.evidence = []
        self.fail = False

    def apply(self, event):
        if self.fail:
            raise ConnectionError("PostgreSQL unavailable")
        self.evidence.append(event)
        return self.outcome


@pytest.fixture
def bundle():
    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    trust = SignedEvidenceTrust(
        "https://revocations.example.test", "cc-privileged",
        {"iam-revocation-1": pub}, "revocation",
    )
    now = int(datetime.now(UTC).timestamp())
    event_id, request_id = uuid4(), uuid4()
    claims = {
        "iss": "https://revocations.example.test", "aud": "cc-privileged",
        "kind": "revocation", "sub": "iam-security-service", "tenant_id": "tenant-a",
        "iat": now - 5, "nbf": now - 5, "exp": now + 120,
        "jti": str(event_id), "request_id": str(request_id),
        "login_role": "cc_runtime_revoked_target", "operation": "rotate",
    }
    return key, trust, claims, event_id, request_id


def service(bundle, *, changes=None, key=None, outcome="TOMBSTONED"):
    signer, trust, claims, _, _ = bundle
    src = Source(_token(key or signer, claims | (changes or {})))
    repo = Repo(outcome)
    return SignedIamRevocationProcessor(
        verifier=PinnedSignedEvidenceVerifier(trust), source=src, repository=repo,
    ), src, repo


def test_signed_preissue_revocation_has_durable_sql_first_ack(bundle):
    svc, source, repo = service(bundle)
    receipt = svc.process(bundle[3])
    assert receipt.disposition == "TOMBSTONED"
    assert receipt.request_id == bundle[4]
    assert source.acks == [receipt]
    assert repo.evidence[0].request_id == bundle[4]
    assert len(repo.evidence[0].signed_digest) == 64
    assert repo.evidence[0].signer_kid == "iam-revocation-1"
    assert "cc_runtime" not in repr(svc)


@pytest.mark.parametrize("outcome", [
    "REVOKED", "ALREADY_CONSUMED", "ALREADY_REVOKED", "TOMBSTONED",
])
def test_distinct_sql_dispositions_are_not_invented(bundle, outcome):
    svc, source, _ = service(bundle, outcome=outcome)
    assert svc.process(bundle[3]).disposition == outcome
    assert len(source.acks) == 1


@pytest.mark.parametrize("changes", [
    {"kind": "operator"}, {"tenant_id": ""}, {"operation": "delete"},
    {"login_role": "postgres"}, {"request_id": "not-a-uuid"},
    {"jti": str(uuid4())}, {"exp": 9999999999},
])
def test_invalid_revocation_scope_or_time_never_writes_sql(bundle, changes):
    svc, source, repo = service(bundle, changes=changes)
    with pytest.raises(PrivilegedAccessDenied):
        svc.process(bundle[3])
    assert not repo.evidence and not source.acks


def test_untrusted_signing_key_cannot_ack(bundle):
    svc, source, repo = service(bundle, key=Ed25519PrivateKey.generate())
    with pytest.raises(PrivilegedAccessDenied):
        svc.process(bundle[3])
    assert not source.acks and not repo.evidence


def test_remote_ack_failure_reports_persisted_local_receipt_for_retry(bundle):
    svc, source, repo = service(bundle, outcome="REVOKED")
    source.fail_ack = True
    with pytest.raises(RemoteAcknowledgementIncomplete) as error:
        svc.process(bundle[3])
    assert error.value.receipt.disposition == "REVOKED"
    assert len(repo.evidence) == 1 and not source.acks
    source.fail_ack = False
    assert svc.process(bundle[3]).disposition == "REVOKED"
    assert len(source.acks) == 1


def test_unavailable_iam_source_fail_closed(bundle):
    svc, source, repo = service(bundle)
    source.fail_read = True
    with pytest.raises(PrivilegedAccessDenied):
        svc.process(bundle[3])
    assert not repo.evidence and not source.acks


def test_unavailable_sql_receipt_prevents_remote_ack(bundle):
    svc, source, repo = service(bundle)
    repo.fail = True
    with pytest.raises(ConnectionError):
        svc.process(bundle[3])
    assert not source.acks


def test_unknown_sql_status_cannot_be_acknowledged(bundle):
    svc, source, _ = service(bundle, outcome="UNRECOGNIZED")
    with pytest.raises(RuntimeError, match="Unknown SQL revocation"):
        svc.process(bundle[3])
    assert not source.acks


def test_revocation_requires_independent_trust_root_and_source(bundle):
    key, trust, claims, _, _ = bundle
    operator_pub = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    with pytest.raises(ValueError):
        SignedIamRevocationProcessor(
            verifier=PinnedSignedEvidenceVerifier(SignedEvidenceTrust(
                "issuer", "aud", {"kid": operator_pub}, "operator",
            )), source=Source(_token(key, claims)), repository=Repo(),
        )
    with pytest.raises(ValueError):
        SignedIamRevocationProcessor(
            verifier=PinnedSignedEvidenceVerifier(trust), source=object(), repository=Repo(),
        )
