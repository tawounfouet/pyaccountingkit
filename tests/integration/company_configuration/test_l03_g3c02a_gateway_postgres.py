"""G3-C02a real SQL: independently signed actor → auth gate → SQL issuer.

The signing key, independently signed IAM decision HTTP stub and service
wiring here are TEST FIXTURES; the full authorization adapter is real.
The nonce store is now real PostgreSQL (G3-C02b1), not a fake local set.
This still does not prove deployment isolation or real human IAM.
"""

import base64
import json
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
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
from pyaccountingkit.company_configuration.application.organization_registration_service import (  # noqa: E402
    OrganizationRegistrationService,
)
from pyaccountingkit.company_configuration.application.service import PermissionDenied  # noqa: E402
from pyaccountingkit.company_configuration.domain.organization.model import (  # noqa: E402
    Company,
    CompanyKind,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import CompanyId  # noqa: E402
from pyaccountingkit.company_configuration.domain.shared.references import (  # noqa: E402
    JurisdictionCode,
)
from pyaccountingkit.company_configuration.infrastructure.iam.http_revocation_source import (  # noqa: E402
    IamHttpResponse,
)
from pyaccountingkit.company_configuration.infrastructure.iam.organization_command_evidence import (  # noqa: E402
    OrganizationCommandTrust,
    PinnedOrganizationCommandVerifier,
)
from pyaccountingkit.company_configuration.infrastructure.iam.organization_live_grants import (  # noqa: E402
    HttpsSignedOrganizationGrantSource,
    SignedLiveGrantTrust,
)
from pyaccountingkit.company_configuration.infrastructure.postgres import (  # noqa: E402
    organization_nonce,
    organization_registration,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
COMPANY_WRITER = os.getenv("CC_PG_ORG_COMPANY_WRITER_DSN")
NONCE_WRITER = os.getenv("CC_PG_ORG_NONCE_CONSUMER_DSN")
pytestmark = pytest.mark.skipif(
    not (ADMIN and RUNTIME and COMPANY_WRITER and NONCE_WRITER),
    reason="G3-C02a gateway/SQL positive integration needs isolated CI identities",
)
NOW = datetime.now(UTC)


class Clock:
    def now(self):
        return NOW


class DDDGrants:
    def require(self, *, principal, action, tenant_id):
        if (principal.actor_id, principal.tenant_id, action, tenant_id) != (
            "verified-actor", "tenant-a", "organization.company.register", "tenant-a",
        ):
            raise PermissionDenied("Independent DDD grant required")


class SignedIamDecisionTransport:
    """Fake remote IAM over an injected transport; no real external service."""

    def __init__(self, private):
        self.private = private
        self.revoked = False
        self.calls = []

    def request(self, method, url, headers, body, timeout):
        assert method == "POST"
        request = json.loads(body)
        self.calls.append(request)
        epoch = int(NOW.timestamp())
        claims = {
            **request,
            "iss": "independent-decision-iam",
            "aud": "org-issuer-gateway-decision",
            "kind": "organization.authorization.decision",
            "allowed": not self.revoked,
            "revoked": self.revoked,
            "grant_id": str(uuid4()),
            "grant_version": 2,
            "iat": epoch, "nbf": epoch, "exp": epoch + 20,
        }
        h = _b64(json.dumps({
            "alg": "EdDSA", "typ": "JWT", "kid": "decision-ephemeral",
        }).encode())
        p = _b64(json.dumps(claims).encode())
        signed = f"{h}.{p}"
        return IamHttpResponse(
            200, "application/jose",
            (signed + "." + _b64(self.private.sign(signed.encode()))).encode(),
        )


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def token(key, command, *, action=None):
    identity = command_identity(command)
    epoch = int(NOW.timestamp())
    claims = {
        "iss": "trusted-iam", "aud": "org-issuer-gateway",
        "kind": "organization.command", "sub": "verified-actor",
        "tenant_id": identity.tenant_id, "action": action or identity.action,
        "target_id": str(identity.target_id), "request_id": identity.request_id,
        "correlation_id": identity.correlation_id, "request_digest": identity.digest,
        "iat": epoch, "nbf": epoch, "exp": epoch + 60, "jti": str(uuid4()),
    }
    header = {"alg": "EdDSA", "typ": "JWT", "kid": "ephemeral"}
    header_str = _b64(json.dumps(header).encode())
    payload_str = _b64(json.dumps(claims).encode())
    message = f"{header_str}.{payload_str}"
    return message + "." + _b64(key.sign(message.encode("ascii")))


def _counts():
    with psycopg.connect(ADMIN) as conn:
        return tuple(
            conn.execute(
                "SELECT count(*) FROM company_configuration." + table
            ).fetchone()[0]
            for table in (
                "organizational_companies", "organization_command_requests",
                "organization_command_audit", "organization_command_outbox",
            )
        )


def _nonce_count():
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            "SELECT count(*) FROM company_configuration.organization_command_nonces"
        ).fetchone()[0]


def test_signed_gateway_commits_once_and_rejects_replays_and_revocation():
    with psycopg.connect(ADMIN) as conn:
        # Truncate parents and FK-bound membership children in ONE statement.
        # No CASCADE: preserve unrelated L02 fixture and migration contract.
        conn.execute(
            "TRUNCATE company_configuration.organization_command_requests,"
            "company_configuration.organization_command_audit,"
            "company_configuration.organization_command_outbox,"
            "company_configuration.organization_membership_requests,"
            "company_configuration.organization_membership_audit,"
            "company_configuration.organization_membership_outbox,"
            "company_configuration.organizational_membership_revisions,"
            "company_configuration.organizational_establishments,"
            "company_configuration.organizational_legal_identifiers,"
            "company_configuration.organizational_companies,"
            "company_configuration.organization_command_nonces"
        )

    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    verifier = PinnedOrganizationCommandVerifier(
        OrganizationCommandTrust(
            issuer="trusted-iam", audience="org-issuer-gateway",
            keys={"ephemeral": public},
        )
    )
    registration = OrganizationRegistrationService(
        lambda: organization_registration.PostgresOrganizationRegistrationUnitOfWork(RUNTIME),
        DDDGrants(), Clock(),
        company_uow_factory=lambda: (
            organization_registration.PostgresOrganizationRegistrationUnitOfWork(
                COMPANY_WRITER
            )
        ),
    )
    decision_key = Ed25519PrivateKey.generate()
    decision_public = decision_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    decision_transport = SignedIamDecisionTransport(decision_key)
    grants = HttpsSignedOrganizationGrantSource(
        origin="https://independent-iam.example.net",
        service_token="ephemeral-test-only",
        trust=SignedLiveGrantTrust(
            issuer="independent-decision-iam",
            audience="org-issuer-gateway-decision",
            keys={"decision-ephemeral": decision_public},
        ),
        transport=decision_transport, clock=Clock(),
    )
    nonce = organization_nonce.PostgresDurableCommandNonceStore(NONCE_WRITER)
    gateway = OrganizationTrustedIssuerGateway(
        verifier=verifier, authorization=grants, nonce_store=nonce,
        executor=OrganizationServiceExecutor(
            registration=registration, lifecycle=object(), membership=object(),
        ), clock=Clock(),
    )
    company = Company(
        CompanyId.new(), "tenant-a", "Signed company",
        CompanyKind.GROUP, JurisdictionCode("FR"),
    )
    command = RegisterCompany(company, "request-1", "corr-1", "approved")

    bad_token = token(key, command, action="organization.membership.assign")
    with pytest.raises(PermissionDenied):
        gateway.execute(command, signed_evidence=bad_token)
    assert _counts() == (0, 0, 0, 0)
    assert _nonce_count() == 0

    signed = token(key, command)
    receipt = gateway.execute(command, signed_evidence=signed)
    assert receipt.revision == 1
    assert _counts() == (1, 1, 1, 1)
    assert _nonce_count() == 1

    with pytest.raises(PermissionDenied):
        gateway.execute(command, signed_evidence=signed)
    assert _counts() == (1, 1, 1, 1)
    assert _nonce_count() == 1

    assert gateway.execute(command, signed_evidence=token(key, command)) == receipt
    assert _counts() == (1, 1, 1, 1)
    assert _nonce_count() == 2

    decision_transport.revoked = True
    with pytest.raises(PermissionDenied):
        gateway.execute(command, signed_evidence=token(key, command))
    assert _counts() == (1, 1, 1, 1)
    assert _nonce_count() == 2
