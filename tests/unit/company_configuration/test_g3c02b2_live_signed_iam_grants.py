"""G3-C02b2: transport-controlled signed IAM grant decisions; no real IdP.

The ephemeral decision signing private key exists ONLY in the tests. Every
authorization invocation must issue a fresh challenge; no cached allow.
"""

import base64
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

cryptography = pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: E402
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives.serialization import (  # noqa: E402
    Encoding,
    PublicFormat,
)

from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal  # noqa: E402
from pyaccountingkit.company_configuration.application.service import PermissionDenied  # noqa: E402
from pyaccountingkit.company_configuration.infrastructure.iam.http_revocation_source import (  # noqa: E402
    IamHttpResponse,
)
from pyaccountingkit.company_configuration.infrastructure.iam.organization_live_grants import (  # noqa: E402
    HttpsSignedOrganizationGrantSource,
    SignedLiveGrantTrust,
)

NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)
ARGS = {
    "issuer": "command-issuer",
    "principal": TrustedPrincipal("actor-a", "tenant-a"),
    "action": "organization.company.register",
    "target_id": uuid4(),
    "request_id": "request-123",
    "correlation_id": "corr-123",
    "request_digest": "a" * 64,
    "command_nonce": uuid4(),
}


class Clock:
    def now(self):
        return NOW


def _b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _sign(private, claims, *, header=None):
    header = header if header is not None else {
        "alg": "EdDSA", "typ": "JWT", "kid": "decision-test-key",
    }
    h = _b64(json.dumps(header, separators=(",", ":")).encode())
    p = _b64(json.dumps(claims, separators=(",", ":")).encode())
    return f"{h}.{p}.{_b64(private.sign(f'{h}.{p}'.encode()))}"


class SignedIamTransport:
    """Authoritative-looking test source; controls are NOT a production IAM."""

    def __init__(self, private):
        self.private = private
        self.changes = {}
        self.status = 200
        self.content_type = "application/jose"
        self.calls = []
        self.fail = False
        self.replayed_response = None
        self.header = None

    def request(self, method, url, headers, body, timeout):
        self.calls.append((method, url, headers, body, timeout))
        if self.fail:
            raise ConnectionError("provider disconnected")
        if self.replayed_response is not None:
            return self.replayed_response
        params = json.loads(body.decode())
        epoch = int(NOW.timestamp())
        claims = {
            **params,
            "iss": "separate-iam-decision-authority",
            "aud": "trusted-organization-gateway",
            "kind": "organization.authorization.decision",
            "allowed": True,
            "revoked": False,
            "grant_id": str(uuid4()),
            "grant_version": 2,
            "iat": epoch, "nbf": epoch, "exp": epoch + 20,
        }
        claims.update(self.changes)
        return IamHttpResponse(
            self.status, self.content_type,
            _sign(self.private, claims, header=self.header).encode("ascii"),
        )


@pytest.fixture
def live():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    trust = SignedLiveGrantTrust(
        issuer="separate-iam-decision-authority",
        audience="trusted-organization-gateway",
        keys={"decision-test-key": public},
    )
    transport = SignedIamTransport(private)
    source = HttpsSignedOrganizationGrantSource(
        origin="https://iam.example.net",
        service_token="test-service-credential",
        trust=trust, transport=transport, clock=Clock(),
    )
    return source, transport


def test_current_signed_grant_is_bound_to_one_specific_command(live):
    source, transport = live
    assert source.require(**ARGS) is None
    assert len(transport.calls) == 1
    method, url, headers, body, timeout = transport.calls[0]
    assert method == "POST"
    assert url == "https://iam.example.net/v1/organization/authorization/decisions"
    assert timeout == 3.0
    assert headers["Cache-Control"] == "no-store"
    assert headers["Accept"] == "application/jose"
    assert json.loads(body)["request_digest"] == ARGS["request_digest"]
    assert "test-service-credential" not in body.decode()
    assert "PRIVATE KEY" not in body.decode()


def test_every_check_must_use_a_new_one_time_iam_challenge(live):
    source, transport = live
    source.require(**ARGS)
    source.require(**ARGS)
    first = json.loads(transport.calls[0][3])
    second = json.loads(transport.calls[1][3])
    assert first["challenge"] != second["challenge"]
    assert len(transport.calls) == 2


@pytest.mark.parametrize("changes", [
    {"allowed": False},
    {"revoked": True},
    {"allowed": 1},
    {"revoked": 0},
    {"iss": "forged-iam"},
    {"aud": "other-gateway"},
    {"kind": "organization.command"},
    {"sub": "other-actor"},
    {"tenant_id": "tenant-b"},
    {"command_issuer": "other-issuer"},
    {"action": "organization.membership.assign"},
    {"target_id": str(uuid4())},
    {"request_id": "other-request"},
    {"correlation_id": "other-correlation"},
    {"request_digest": "b" * 64},
    {"command_nonce": str(uuid4())},
    {"challenge": str(uuid4())},
    {"grant_version": 0},
    {"grant_version": True},
    {"grant_id": "invalid"},
    {"exp": int((NOW - timedelta(seconds=2)).timestamp())},
    {"nbf": int((NOW + timedelta(seconds=10)).timestamp())},
    {"exp": int((NOW + timedelta(minutes=2)).timestamp())},
    {"exp": True},
    {"unexpected": "extra"},
])
def test_signed_denial_revocation_or_scope_mismatch_fails_closed(live, changes):
    source, transport = live
    transport.changes = changes
    with pytest.raises(PermissionDenied):
        source.require(**ARGS)


def test_replaying_a_previous_authorization_decision_is_rejected(live):
    source, transport = live
    valid = transport.request("POST", "https://iam.example.net", {}, json.dumps({
        "command_issuer": ARGS["issuer"],
        "sub": ARGS["principal"].actor_id,
        "tenant_id": ARGS["principal"].tenant_id,
        "action": ARGS["action"],
        "target_id": str(ARGS["target_id"]),
        "request_id": ARGS["request_id"],
        "correlation_id": ARGS["correlation_id"],
        "request_digest": ARGS["request_digest"],
        "command_nonce": str(ARGS["command_nonce"]),
        "challenge": str(uuid4()),
    }).encode(), 3.0)
    transport.replayed_response = valid
    with pytest.raises(PermissionDenied):
        source.require(**ARGS)


@pytest.mark.parametrize("header", [
    {"alg": "none", "typ": "JWT", "kid": "decision-test-key"},
    {"alg": "HS256", "typ": "JWT", "kid": "decision-test-key"},
    {"alg": "EdDSA", "typ": "JWT", "kid": "unknown-key"},
])
def test_untrusted_jws_signing_headers_rejected(live, header):
    source, transport = live
    transport.header = header
    with pytest.raises(PermissionDenied):
        source.require(**ARGS)


def test_outage_or_bad_response_cannot_be_interpreted_as_allow(live):
    source, transport = live
    transport.fail = True
    with pytest.raises(PermissionDenied):
        source.require(**ARGS)
    transport.fail = False
    transport.status = 204
    with pytest.raises(PermissionDenied):
        source.require(**ARGS)
    transport.status = 200
    transport.content_type = "text/plain"
    with pytest.raises(PermissionDenied):
        source.require(**ARGS)


def test_malformed_signature_or_wrong_public_key_is_rejected(live):
    source, transport = live
    impostor = Ed25519PrivateKey.generate()
    transport.private = impostor
    with pytest.raises(PermissionDenied):
        source.require(**ARGS)


@pytest.mark.parametrize("origin", [
    "http://iam.example.net", "https://localhost", "https://127.0.0.1",
    "https://iam.example.net/path", "https://user:pass@iam.example.net",
    "https://iam.example.net/?redirect=1",
])
def test_origin_pinning_rejects_insecure_transport(origin):
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    trust = SignedLiveGrantTrust("decision-iam", "gateway", {"k": public})
    with pytest.raises(ValueError):
        HttpsSignedOrganizationGrantSource(
            origin=origin, service_token="test", trust=trust,
        )


def test_repr_never_leaks_secret(live):
    source, _ = live
    assert "test-service-credential" not in repr(source)
    assert "<redacted>" in repr(source)
