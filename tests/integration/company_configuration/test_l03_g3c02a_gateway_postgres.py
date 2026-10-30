"""G3-C02a real SQL: independently signed actor → auth gate → SQL issuer.

The signing key, nonce state and service wiring here are TEST FIXTURES, not a
deployed distinct IAM/gateway host or production nonce/credential service.
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
from pyaccountingkit.company_configuration.infrastructure.iam.organization_command_evidence import (  # noqa: E402
    OrganizationCommandTrust,
    PinnedOrganizationCommandVerifier,
)
from pyaccountingkit.company_configuration.infrastructure.postgres import (  # noqa: E402
    organization_registration,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
COMPANY_WRITER = os.getenv("CC_PG_ORG_COMPANY_WRITER_DSN")
pytestmark = pytest.mark.skipif(
    not (ADMIN and RUNTIME and COMPANY_WRITER),
    reason="G3-C02a gateway/SQL positive integration needs isolated CI identities",
)
NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)


class Clock:
    def now(self):
        return NOW


class DDDGrants:
    def require(self, *, principal, action, tenant_id):
        if (principal.actor_id, principal.tenant_id, action, tenant_id) != (
            "verified-actor", "tenant-a", "organization.company.register", "tenant-a",
        ):
            raise PermissionDenied("Independent DDD grant required")


class LiveGrants:
    def __init__(self):
        self.enabled = True

    def require(self, *, issuer, principal, action, target_id):
        if not self.enabled or (
            issuer, principal.actor_id, principal.tenant_id, action
        ) != (
            "trusted-iam", "verified-actor", "tenant-a", "organization.company.register",
        ):
            raise PermissionDenied("Current grant revoked")


class NonceTestDouble:
    def __init__(self):
        self.used = set()

    def consume(self, *, issuer, nonce, expires_at):
        if (issuer, nonce) in self.used:
            return False
        self.used.add((issuer, nonce))
        return True


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


def test_signed_gateway_commits_once_and_rejects_replays_and_revocation():
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "TRUNCATE company_configuration.organization_command_requests,"
            "company_configuration.organization_command_audit,"
            "company_configuration.organization_command_outbox"
        )
        conn.execute(
            "TRUNCATE company_configuration.organizational_companies"
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
        company_uow_factory=lambda: organization_registration.PostgresOrganizationRegistrationUnitOfWork(
            COMPANY_WRITER
        ),
    )
    grants, nonce = LiveGrants(), NonceTestDouble()
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

    signed = token(key, command)
    receipt = gateway.execute(command, signed_evidence=signed)
    assert receipt.revision == 1
    assert _counts() == (1, 1, 1, 1)

    with pytest.raises(PermissionDenied):
        gateway.execute(command, signed_evidence=signed)
    assert _counts() == (1, 1, 1, 1)

    assert gateway.execute(command, signed_evidence=token(key, command)) == receipt
    assert _counts() == (1, 1, 1, 1)

    grants.enabled = False
    with pytest.raises(PermissionDenied):
        gateway.execute(command, signed_evidence=token(key, command))
    assert _counts() == (1, 1, 1, 1)
