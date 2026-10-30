"""G3-C02a adversarial signed-envelope and actor-grant gate tests.

Only these TEST fixtures own an ephemeral private key or in-memory nonce set.
Neither is a production IAM issuer nor a durable multi-instance nonce store.
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

from pyaccountingkit.company_configuration.application.organization_issuer_gateway import (  # noqa: E402
    OrganizationServiceExecutor,
    OrganizationTrustedIssuerGateway,
    command_identity,
)
from pyaccountingkit.company_configuration.application.organization_registration import (  # noqa: E402
    RegisterCompany,
)
from pyaccountingkit.company_configuration.application.service import (  # noqa: E402
    PermissionDenied,
)
from pyaccountingkit.company_configuration.domain.organization.model import (  # noqa: E402
    Company,
    CompanyKind,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import CompanyId  # noqa: E402
from pyaccountingkit.company_configuration.domain.shared.references import (  # noqa: E402
    JurisdictionCode,
)
from pyaccountingkit.company_configuration.infrastructure.iam.organization_command_evidence import (  # noqa: E402
    OrganizationCommandTrust,
    PinnedOrganizationCommandVerifier,
)

NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)


class Clock:
    def __init__(self):
        self.instant = NOW

    def now(self):
        return self.instant


class LiveGrants:
    def __init__(self):
        self.allowed = True
        self.calls = []

    def require(self, *, issuer, principal, action, target_id):
        self.calls.append((issuer, principal.actor_id, principal.tenant_id, action, target_id))
        if not self.allowed:
            raise PermissionDenied("Revoked grant")


class AtomicNonceMock:
    """Single-process atomic contract test double; NOT a production store."""

    def __init__(self):
        self.used = set()
        self.available = True

    def consume(self, *, tenant_id, issuer, nonce, expires_at):
        if not self.available:
            return False
        if (issuer, nonce) in self.used:
            return False
        self.used.add((issuer, nonce))
        return True


class FakeExecutor:
    def __init__(self):
        self.received = []

    def execute(self, *, action, command, principal):
        self.received.append((action, command, principal))
        return ("committed", principal.actor_id)


def _b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def command(tenant="tenant-a", name="Research"):
    item = Company(
        CompanyId.new(), tenant, name, CompanyKind.GROUP, JurisdictionCode("FR"),
    )
    return RegisterCompany(item, "request-1", "correlation-1", "approved")


def _sign(private, claims, *, header=None):
    header = header or {"alg": "EdDSA", "typ": "JWT", "kid": "trusted-key"}
    part1 = _b64(json.dumps(header, separators=(",", ":")).encode())
    part2 = _b64(json.dumps(claims, separators=(",", ":")).encode())
    signature = private.sign(f"{part1}.{part2}".encode("ascii"))
    return f"{part1}.{part2}.{_b64(signature)}"


@pytest.fixture
def harness():
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    trust = OrganizationCommandTrust(
        issuer="trusted-iam", audience="organization-gateway",
        keys={"trusted-key": public},
    )
    verifier = PinnedOrganizationCommandVerifier(trust)
    auth, nonce, executor, clock = LiveGrants(), AtomicNonceMock(), FakeExecutor(), Clock()
    gateway = OrganizationTrustedIssuerGateway(
        verifier=verifier, authorization=auth, nonce_store=nonce,
        executor=executor, clock=clock,
    )
    return key, auth, nonce, executor, clock, gateway


def claims(item, *, nonce=None):
    identity = command_identity(item)
    now = int(NOW.timestamp())
    return {
        "iss": "trusted-iam",
        "aud": "organization-gateway",
        "kind": "organization.command",
        "sub": "verified-operator",
        "tenant_id": identity.tenant_id,
        "action": identity.action,
        "target_id": str(identity.target_id),
        "request_id": identity.request_id,
        "correlation_id": identity.correlation_id,
        "request_digest": identity.digest,
        "iat": now, "nbf": now, "exp": now + 60,
        "jti": str(nonce or uuid4()),
    }


def test_verified_request_reaches_executor_with_derived_principal(harness):
    private, auth, nonce, executor, _, gateway = harness
    item = command()
    token = _sign(private, claims(item))
    assert gateway.execute(item, signed_evidence=token) == (
        "committed", "verified-operator",
    )
    assert executor.received[0][2].actor_id == "verified-operator"
    assert executor.received[0][2].tenant_id == "tenant-a"
    assert auth.calls[0][3] == "organization.company.register"
    assert len(nonce.used) == 1


@pytest.mark.parametrize("changed", [
    {"sub": " impersonated"},
    {"tenant_id": "tenant-b"},
    {"action": "organization.membership.assign"},
    {"target_id": str(uuid4())},
    {"request_id": "different"},
    {"correlation_id": "different"},
    {"request_digest": "a" * 64},
    {"aud": "other-gateway"},
    {"kind": "operator"},
    {"iss": "unknown-iam"},
    {"nbf": int((NOW + timedelta(seconds=40)).timestamp())},
    {"exp": int((NOW - timedelta(seconds=1)).timestamp())},
])
def test_forged_or_mismatched_claim_denied_before_sql(harness, changed):
    private, _, nonce, executor, _, gateway = harness
    item = command()
    fake = claims(item)
    fake.update(changed)
    with pytest.raises(PermissionDenied):
        gateway.execute(item, signed_evidence=_sign(private, fake))
    assert not executor.received
    assert not nonce.used


def test_signed_command_mutation_never_authorizes_a_different_payload(harness):
    private, _, nonce, executor, _, gateway = harness
    source = command()
    other = RegisterCompany(
        Company(source.company.id, "tenant-a", "Forged new name",
                CompanyKind.GROUP, JurisdictionCode("FR")),
        source.request_id, source.correlation_id, source.reason,
    )
    with pytest.raises(PermissionDenied):
        gateway.execute(other, signed_evidence=_sign(private, claims(source)))
    assert not executor.received
    assert not nonce.used


def test_modified_jws_signature_fails_closed_before_live_iam(harness):
    private, auth, nonce, executor, _, gateway = harness
    item = command()
    original = _sign(private, claims(item))
    header, payload, signature = original.split(".")
    corrupted = _b64(b"\x00" * 64)
    with pytest.raises(PermissionDenied):
        gateway.execute(item, signed_evidence=f"{header}.{payload}.{corrupted}")
    assert not auth.calls
    assert not nonce.used
    assert not executor.received


def test_algorithm_switch_and_unknown_key_rejected(harness):
    private, auth, nonce, executor, _, gateway = harness
    item = command()
    for header in (
        {"alg": "none", "typ": "JWT", "kid": "trusted-key"},
        {"alg": "EdDSA", "typ": "JWT", "kid": "untrusted-key"},
    ):
        with pytest.raises(PermissionDenied):
            gateway.execute(
                item, signed_evidence=_sign(private, claims(item), header=header),
            )
    assert not auth.calls and not nonce.used and not executor.received


def test_current_iam_revocation_preempts_nonce_and_sql(harness):
    private, auth, nonce, executor, _, gateway = harness
    item = command()
    auth.allowed = False
    with pytest.raises(PermissionDenied):
        gateway.execute(item, signed_evidence=_sign(private, claims(item)))
    assert auth.calls and not nonce.used and not executor.received


def test_repeat_nonce_is_denied_but_new_attestation_allows_service_replay(harness):
    private, _, nonce, executor, _, gateway = harness
    item = command()
    token = _sign(private, claims(item))
    assert gateway.execute(item, signed_evidence=token)[0] == "committed"
    with pytest.raises(PermissionDenied):
        gateway.execute(item, signed_evidence=token)
    assert len(executor.received) == 1
    token2 = _sign(private, claims(item))
    assert gateway.execute(item, signed_evidence=token2)[0] == "committed"
    assert len(executor.received) == 2


def test_unavailable_nonce_store_is_fail_closed(harness):
    private, _, nonce, executor, _, gateway = harness
    item = command()
    nonce.available = False
    with pytest.raises(PermissionDenied):
        gateway.execute(item, signed_evidence=_sign(private, claims(item)))
    assert not executor.received


def test_expired_token_not_allowed_after_clock_advance(harness):
    private, _, nonce, executor, clock, gateway = harness
    item = command()
    token = _sign(private, claims(item))
    clock.instant += timedelta(minutes=3)
    with pytest.raises(PermissionDenied):
        gateway.execute(item, signed_evidence=token)
    assert not executor.received and not nonce.used


def test_trust_rejects_missing_invalid_public_keys():
    with pytest.raises(ValueError):
        OrganizationCommandTrust(
            issuer="trusted-iam", audience="org", keys={"invalid": b"short"},
        )


def test_service_executor_preserves_ddd_dispatch_and_principal():
    class Service:
        def register_company(self, item, *, principal):
            return "reg", item, principal

        def assign(self, item, *, principal):
            return "member", item, principal

    service = Service()
    adapter = OrganizationServiceExecutor(
        registration=service, lifecycle=service, membership=service,
    )
    item = command()
    from pyaccountingkit.company_configuration.application.ports import TrustedPrincipal

    principal = TrustedPrincipal("verified", "tenant-a")
    assert adapter.execute(
        action="organization.company.register", command=item, principal=principal,
    ) == ("reg", item, principal)
    with pytest.raises(PermissionDenied):
        adapter.execute(
            action="organization.membership.assign", command=item, principal=principal,
        )
