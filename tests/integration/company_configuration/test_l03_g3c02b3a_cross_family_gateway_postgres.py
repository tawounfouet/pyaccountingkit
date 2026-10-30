"""G3-C02b3a: all 7 signed gateway actions to 4 SQL issuer families.

This is *R&D* full-path proof: an ephemeral Ed25519 command issuer and fake
HTTPS IAM source, real Ed25519 verification, real durable PostgreSQL nonce and
real domain SQL issuers. Neither private key nor live grant mock is production.
"""

import base64
import json
import os
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: E402
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives.serialization import (  # noqa: E402
    Encoding,
    PublicFormat,
)

from pyaccountingkit.company_configuration.application.organization_commands import (  # noqa: E402
    AssignOrganizationMembership,
    EndOrganizationMembership,
)
from pyaccountingkit.company_configuration.application.organization_issuer_gateway import (  # noqa: E402
    OrganizationServiceExecutor,
    OrganizationTrustedIssuerGateway,
    command_identity,
)
from pyaccountingkit.company_configuration.application.organization_lifecycle import (  # noqa: E402
    TransitionCompany,
    TransitionEstablishment,
)
from pyaccountingkit.company_configuration.application.organization_lifecycle_service import (  # noqa: E402
    OrganizationLifecycleService,
)
from pyaccountingkit.company_configuration.application.organization_registration import (  # noqa: E402
    RegisterCompany,
    RegisterEstablishment,
    RegisterLegalIdentifier,
)
from pyaccountingkit.company_configuration.application.organization_registration_service import (  # noqa: E402
    OrganizationRegistrationService,
)
from pyaccountingkit.company_configuration.application.organization_service import (  # noqa: E402
    OrganizationMembershipService,
)
from pyaccountingkit.company_configuration.application.service import PermissionDenied  # noqa: E402
from pyaccountingkit.company_configuration.domain.organization.model import (  # noqa: E402
    Company,
    CompanyKind,
    CompanyStatus,
    Establishment,
    EstablishmentStatus,
    LegalIdentifier,
    MembershipKind,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (  # noqa: E402
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (  # noqa: E402
    EffectiveInterval,
)
from pyaccountingkit.company_configuration.domain.shared.identifiers import (  # noqa: E402
    CompanyId,
    EstablishmentId,
    LegalEntityId,
    MembershipId,
)
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
    organization_registration,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.organization_lifecycle import (  # noqa: E402
    PostgresOrganizationLifecycleUnitOfWork,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.organization_membership import (  # noqa: E402
    PostgresOrganizationMembershipUnitOfWork,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.organization_nonce import (  # noqa: E402
    PostgresDurableCommandNonceStore,
)

RegistrationUoW = organization_registration.PostgresOrganizationRegistrationUnitOfWork

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
WRITERS = {
    "company": os.getenv("CC_PG_ORG_COMPANY_WRITER_DSN"),
    "registry": os.getenv("CC_PG_ORG_REGISTRY_WRITER_DSN"),
    "lifecycle": os.getenv("CC_PG_ORG_LIFECYCLE_WRITER_DSN"),
    "membership": os.getenv("CC_PG_ORG_MEMBERSHIP_WRITER_DSN"),
    "nonce": os.getenv("CC_PG_ORG_NONCE_CONSUMER_DSN"),
}
pytestmark = pytest.mark.skipif(
    not ADMIN or not RUNTIME or not all(WRITERS.values()),
    reason="G3-C02b3a requires all independent tenant SQL issuer test credentials",
)


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class Clock:
    def now(self):
        return datetime.now(UTC)


class DomainGrant:
    """Only test-side domain action grants; actor remains signature-derived."""

    def require(self, *, principal, action, tenant_id=None, scope=None):
        tenant = tenant_id if tenant_id is not None else scope.tenant_id
        if principal.actor_id != "verified-operator" or (
            principal.tenant_id != tenant or tenant != "tenant-a"
        ):
            raise PermissionDenied("Domain authorization refused")


class DecisionHttpStub:
    """Not an IAM provider: only supplies signed response test vectors."""

    def __init__(self, key):
        self.key = key
        self.revoked = False
        self.allowed = True
        self.calls = []
        self.on_decision = None

    def request(self, method, url, headers, body, timeout):
        assert method == "POST"
        req = json.loads(body)
        self.calls.append(req)
        current = int(datetime.now(UTC).timestamp())
        data = {
            **req, "iss": "decision-iam", "aud": "org-gateway-decision",
            "kind": "organization.authorization.decision",
            "allowed": self.allowed, "revoked": self.revoked,
            "grant_id": str(uuid4()), "grant_version": 2,
            "iat": current, "nbf": current, "exp": current + 20,
        }
        h = _b64(json.dumps({
            "alg": "EdDSA", "typ": "JWT", "kid": "iam-decision",
        }).encode())
        p = _b64(json.dumps(data).encode())
        message = f"{h}.{p}"
        signed = message + "." + _b64(self.key.sign(message.encode()))
        if self.on_decision is not None:
            self.on_decision()
        return IamHttpResponse(200, "application/jose", signed.encode())


class Harness:
    def __init__(self):
        self.command_key = Ed25519PrivateKey.generate()
        decision_key = Ed25519PrivateKey.generate()
        self.iam = DecisionHttpStub(decision_key)
        def public(key):
            return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        verifier = PinnedOrganizationCommandVerifier(
            OrganizationCommandTrust(
                issuer="trusted-iam", audience="org-gateway",
                keys={"command-signing": public(self.command_key)},
            )
        )
        grants = HttpsSignedOrganizationGrantSource(
            origin="https://independent-iam.example.net",
            service_token="test-only-credential",
            trust=SignedLiveGrantTrust(
                issuer="decision-iam", audience="org-gateway-decision",
                keys={"iam-decision": public(decision_key)},
            ),
            transport=self.iam, clock=Clock(),
        )
        auth = DomainGrant()
        registration = OrganizationRegistrationService(
            lambda: RegistrationUoW(RUNTIME),
            auth, Clock(),
            company_uow_factory=lambda: RegistrationUoW(
                WRITERS["company"]
            ),
            registry_uow_factory=lambda: RegistrationUoW(
                WRITERS["registry"]
            ),
        )
        lifecycle = OrganizationLifecycleService(
            lambda: PostgresOrganizationLifecycleUnitOfWork(WRITERS["lifecycle"]),
            auth, Clock(),
        )
        membership = OrganizationMembershipService(
            lambda: PostgresOrganizationMembershipUnitOfWork(WRITERS["membership"]),
            auth, Clock(),
        )
        self.gateway = OrganizationTrustedIssuerGateway(
            verifier=verifier, authorization=grants,
            nonce_store=PostgresDurableCommandNonceStore(WRITERS["nonce"]),
            executor=OrganizationServiceExecutor(
                registration=registration, lifecycle=lifecycle, membership=membership,
            ), clock=Clock(),
        )

    def sign(self, command, *, alter=None):
        identity = command_identity(command)
        instant = int(datetime.now(UTC).timestamp())
        data = {
            "iss": "trusted-iam", "aud": "org-gateway",
            "kind": "organization.command", "sub": "verified-operator",
            "tenant_id": identity.tenant_id, "action": identity.action,
            "target_id": str(identity.target_id),
            "request_id": identity.request_id, "correlation_id": identity.correlation_id,
            "request_digest": identity.digest,
            "iat": instant, "nbf": instant, "exp": instant + 60,
            "jti": str(uuid4()),
        }
        data.update(alter or {})
        header = _b64(json.dumps({
            "alg": "EdDSA", "typ": "JWT", "kid": "command-signing",
        }).encode())
        payload = _b64(json.dumps(data).encode())
        signing_input = f"{header}.{payload}"
        return signing_input + "." + _b64(
            self.command_key.sign(signing_input.encode())
        )

    def run(self, command):
        return self.gateway.execute(command, signed_evidence=self.sign(command))


TABLES = (
    "organizational_companies", "organizational_establishments",
    "organizational_legal_identifiers",
    "organization_command_requests", "organization_command_audit",
    "organization_command_outbox",
    "organizational_company_revisions", "organizational_establishment_revisions",
    "organization_lifecycle_requests", "organization_lifecycle_audit",
    "organization_lifecycle_outbox",
    "organizational_membership_revisions", "organization_membership_requests",
    "organization_membership_audit", "organization_membership_outbox",
    "organization_command_nonces",
)


def counts():
    with psycopg.connect(ADMIN) as conn:
        return {
            table: conn.execute(
                "SELECT count(*) FROM company_configuration." + table
            ).fetchone()[0]
            for table in TABLES
        }


@pytest.fixture(autouse=True)
def clear_command_evidence():
    if not ADMIN:
        yield
        return

    def reset():
        with psycopg.connect(ADMIN) as conn:
            conn.execute(
                "TRUNCATE " + ",".join(
                    "company_configuration." + item for item in TABLES
                )
            )

    reset()
    yield
    reset()


def legal_parent():
    parent = LegalEntityId.new()
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "INSERT INTO company_configuration.legal_entities "
            "(tenant_id,company_id,entity_id,legal_name,jurisdiction,"
            "functional_currency,revision) VALUES (%s,%s,%s,%s,%s,%s,1)",
            ("tenant-a", uuid4(), parent.value, "Test legal", "FR", "EUR"),
        )
    return parent


def build_commands():
    company = Company(
        CompanyId.new(), "tenant-a", "Signed Group",
        CompanyKind.GROUP, JurisdictionCode("FR"),
    )
    legal = legal_parent()
    site = Establishment(
        EstablishmentId.new(), "tenant-a", legal, "Test Office",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)),
    )
    identifier = LegalIdentifier(
        "tenant-a", legal, "SIREN", "987654321", "INSEE",
        JurisdictionCode("FR"), EffectiveInterval(date(2026, 1, 1)), "registry",
    )
    scope = ConfigurationScope("tenant-a", company.id, legal)
    mid = MembershipId.new()
    return (
        RegisterCompany(company, "company-reg", "c-company", "board"),
        RegisterEstablishment(site, "site-reg", "c-site", "board"),
        RegisterLegalIdentifier(uuid4(), identifier, "id-reg", "c-id", "board"),
        TransitionCompany(
            "tenant-a", company.id, CompanyStatus.ACTIVE, 1,
            "minutes", "company-act", "c-company-act", "approved",
        ),
        TransitionEstablishment(
            "tenant-a", site.id, EstablishmentStatus.ACTIVE, 1,
            "minutes", "site-act", "c-site-act", "approved",
        ),
        AssignOrganizationMembership(
            scope, mid, MembershipKind.ADMINISTRATIVE, True,
            date(2026, 1, 1), None, "minutes",
            "member-assign", "c-member", "approved",
        ),
        EndOrganizationMembership(
            scope, mid, date(2026, 3, 1), 1, "minutes",
            "member-end", "c-end", "approved",
        ),
    )


def test_all_seven_signed_org_commands_use_exact_sql_issuer_and_atomic_evidence():
    h = Harness()
    commands = build_commands()
    expected_rows = (
        ("organizational_companies", "organization_command_requests",
         "organization_command_audit", "organization_command_outbox"),
        ("organizational_establishments", "organization_command_requests",
         "organization_command_audit", "organization_command_outbox"),
        ("organizational_legal_identifiers", "organization_command_requests",
         "organization_command_audit", "organization_command_outbox"),
        ("organizational_company_revisions", "organization_lifecycle_requests",
         "organization_lifecycle_audit", "organization_lifecycle_outbox"),
        ("organizational_establishment_revisions", "organization_lifecycle_requests",
         "organization_lifecycle_audit", "organization_lifecycle_outbox"),
        ("organizational_membership_revisions", "organization_membership_requests",
         "organization_membership_audit", "organization_membership_outbox"),
        ("organizational_membership_revisions", "organization_membership_requests",
         "organization_membership_audit", "organization_membership_outbox"),
    )
    for index, command in enumerate(commands):
        baseline = counts()
        old_calls = len(h.iam.calls)
        # A mismatched signed action is not an authorization, even with valid
        # ephemeral test signature. Neither the nonce nor SQL audit is touched.
        bad = h.sign(command, alter={"action": "organization.company.register"})
        if index != 0:
            with pytest.raises(PermissionDenied):
                h.gateway.execute(command, signed_evidence=bad)
            assert counts() == baseline
        signed = h.sign(command)
        receipt = h.gateway.execute(command, signed_evidence=signed)
        after = counts()
        assert len(h.iam.calls) == old_calls + 1
        assert after["organization_command_nonces"] == baseline[
            "organization_command_nonces"
        ] + 1
        for table in expected_rows[index]:
            assert after[table] == baseline[table] + 1, (index, table, after)
        assert after["organization_command_nonces"] == 2 * index + 1
        # Replay with the same signed JTI is rejected *before* domain SQL.
        with pytest.raises(PermissionDenied):
            h.gateway.execute(command, signed_evidence=signed)
        assert counts() == after
        # A fresh independent signature + same request key returns the same
        # domain receipt and burns a new nonce, but duplicates no SQL evidence.
        assert h.run(command) == receipt
        after_replay = counts()
        assert after_replay["organization_command_nonces"] == 2 * index + 2
        for table in TABLES[:-1]:
            assert after_replay[table] == after[table]
        # Real signed IAM negative decision: do not burn nonce or mutate SQL.
        h.iam.revoked = True
        with pytest.raises(PermissionDenied):
            h.run(command)
        assert counts() == after_replay
        h.iam.revoked = False
        # Subsequent steps start from committed domain objects.
        # Distinct extra replay nonce rows are counted from real SQL.
    assert len(h.iam.calls) >= 14


def test_revocation_after_signed_positive_decision_before_sql_commit_is_not_atomic():
    """Red-team observation: live IAM signed allow != commit-time grant check.

    Even an authentic signed allow at T1 can be revoked at T2, during a
    downstream SQL transaction. Current G3 gateway does not revalidate at
    COMMIT. This test records the *gap*, not a revocation guarantee.
    """
    h = Harness()
    command = build_commands()[0]
    decision_at_sql = []

    def revoke_before_commit():
        h.iam.revoked = True
        decision_at_sql.append(True)

    # Override the executor's Company service only, with the same real
    # issuer-only SQL identity and injected after-write precommit hook.
    registration = OrganizationRegistrationService(
        lambda: RegistrationUoW(RUNTIME),
        DomainGrant(), Clock(),
        company_uow_factory=lambda: RegistrationUoW(
            WRITERS["company"], before_commit=revoke_before_commit,
        ),
    )
    h.gateway._executor = OrganizationServiceExecutor(
        registration=registration, lifecycle=object(), membership=object(),
    )
    first = counts()
    receipt = h.run(command)
    assert receipt.revision == 1 and decision_at_sql and h.iam.revoked
    assert counts()["organizational_companies"] == first[
        "organizational_companies"
    ] + 1
    assert counts()["organization_command_nonces"] == first[
        "organization_command_nonces"
    ] + 1
    # A *new* request after revocation is denied, no additional nonce/rows.
    second = counts()
    with pytest.raises(PermissionDenied):
        h.run(command)
    assert counts() == second
