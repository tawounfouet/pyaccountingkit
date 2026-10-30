"""G3-C02b3b2b1: reverify raw IAM JWS before owner SQL epoch projection.

Test IAM signing key is EPHEMERAL; this is neither deployed IdP nor deployed
vault/owner projection credential certification. No DDD issuer wiring yet.
"""

import base64
import json
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
pytest.importorskip("cryptography")

from cryptography.hazmat.primitives.asymmetric.ed25519 import (  # noqa: E402
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives.serialization import (  # noqa: E402
    Encoding, PublicFormat,
)

from pyaccountingkit.company_configuration.application.service import (  # noqa: E402
    PermissionDenied,
)
from pyaccountingkit.company_configuration.infrastructure.iam.organization_grant_projection import (  # noqa: E402
    GrantProjectionConflict,
    PinnedIamGrantProjectionVerifier,
    PostgresVerifiedIamGrantProjector,
)
from pyaccountingkit.company_configuration.infrastructure.iam.organization_live_grants import (  # noqa: E402
    SignedLiveGrantTrust,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.organization_actor_grant_epoch import (  # noqa: E402
    ActorGrantEpochReference,
    PostgresActorGrantEpochFence,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
COMPANY = os.getenv("CC_PG_ORG_COMPANY_WRITER_DSN")
REGISTRY = os.getenv("CC_PG_ORG_REGISTRY_WRITER_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
NONCE = os.getenv("CC_PG_ORG_NONCE_CONSUMER_DSN")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, COMPANY, REGISTRY, RUNTIME, NONCE)),
    reason="G3-C02b3b2b1 requires ephemeral PG16 owner and tenant login roles",
)
RECEIPTS = "company_configuration.organization_actor_grant_decision_receipts"
EPOCHS = "company_configuration.organization_actor_grant_epochs"


def _b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _sign(private, claims, header=None):
    header = header if header is not None else {
        "alg": "EdDSA", "typ": "JWT", "kid": "ephemeral-decision",
    }
    a = _b64(json.dumps(header, separators=(",", ":")).encode())
    b = _b64(json.dumps(claims, separators=(",", ":")).encode())
    value = f"{a}.{b}"
    return value + "." + _b64(private.sign(value.encode()))


class ProjectionFixture:
    def __init__(self):
        self.private = Ed25519PrivateKey.generate()
        public = self.private.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw,
        )
        self.verifier = PinnedIamGrantProjectionVerifier(
            SignedLiveGrantTrust(
                issuer="independent-iam-test",
                audience="organization-gateway",
                keys={"ephemeral-decision": public},
            )
        )
        self.projector = PostgresVerifiedIamGrantProjector(
            owner_dsn=ADMIN, verifier=self.verifier,
        )
        self.now = datetime.now(UTC)
        self.grant_id = uuid4()
        self.target_id = uuid4()

    def claims(self, **changes):
        stamp = int(self.now.timestamp())
        data = {
            "iss": "independent-iam-test", "aud": "organization-gateway",
            "kind": "organization.authorization.decision",
            "command_issuer": "trusted-command-issuer", "sub": "verified-actor",
            "tenant_id": "tenant-a", "action": "organization.company.register",
            "target_id": str(self.target_id), "request_id": "request-1",
            "correlation_id": "correlation-1",
            "request_digest": "a" * 64,
            "command_nonce": str(uuid4()), "challenge": str(uuid4()),
            "allowed": True, "revoked": False,
            "grant_id": str(self.grant_id), "grant_version": 1,
            "iat": stamp - 1, "nbf": stamp - 1, "exp": stamp + 20,
        }
        data.update(changes)
        return data

    def token(self, **changes):
        return _sign(self.private, self.claims(**changes))

    def project(self, signed):
        return self.projector.project(signed, at=self.now)


@pytest.fixture(autouse=True)
def erase_test_grants():
    if ADMIN:
        with psycopg.connect(ADMIN) as conn:
            conn.execute("TRUNCATE " + RECEIPTS + ", " + EPOCHS)
    yield
    if ADMIN:
        with psycopg.connect(ADMIN) as conn:
            conn.execute("TRUNCATE " + RECEIPTS + ", " + EPOCHS)


def _count(table):
    with psycopg.connect(ADMIN) as conn:
        return conn.execute("SELECT count(*) FROM " + table).fetchone()[0]


def test_verified_iam_jws_projects_one_grant_and_immutable_receipt_atomically():
    fixture = ProjectionFixture()
    signed = fixture.token()
    assert "test" not in repr(fixture.projector) or "<redacted>" in repr(
        fixture.projector
    )
    assert fixture.project(signed) is True
    assert _count(RECEIPTS) == 1
    assert _count(EPOCHS) == 1
    assert fixture.project(signed) is False
    assert (_count(RECEIPTS), _count(EPOCHS)) == (1, 1)

    with psycopg.connect(ADMIN) as conn:
        row = conn.execute(
            "SELECT grant_id,grant_version,actor_id,action,tenant_id,"
            "target_id,decision_sha256,source_event_id,enabled "
            "FROM " + EPOCHS,
        ).fetchone()
        receipt = conn.execute(
            "SELECT decision_sha256,signing_key_id,request_id,"
            "correlation_id,command_issuer,request_digest,allowed,revoked "
            "FROM " + RECEIPTS,
        ).fetchone()
    assert row[0] == fixture.grant_id and row[1] == 1
    assert (row[2], row[3], row[4], row[5], row[8]) == (
        "verified-actor", "organization.company.register",
        "tenant-a", fixture.target_id, True,
    )
    assert receipt == (
        row[6], "ephemeral-decision", "request-1", "correlation-1",
        "trusted-command-issuer", "a" * 64, True, False,
    )
    assert row[7] is not None

    # Only the previously signed decision metadata is a DB reference; even
    # this cannot be forged by an ordinary app or business SQL login.
    scope = ActorGrantEpochReference(
        tenant_id="tenant-a", grant_id=row[0], grant_version=1,
        actor_id=row[2], action=row[3], target_id=row[5],
        authority_issuer="independent-iam-test", decision_sha256=row[6],
    )
    with psycopg.connect(COMPANY) as conn:
        PostgresActorGrantEpochFence().require(connection=conn, reference=scope)


def test_higher_signed_epoch_revokes_owner_projection_and_stale_scope():
    f = ProjectionFixture()
    initial = f.token()
    assert f.project(initial)
    revoke = f.token(grant_version=2, allowed=False, revoked=True)
    assert f.project(revoke)
    with psycopg.connect(ADMIN) as conn:
        rows = conn.execute(
            "SELECT grant_version,enabled FROM " + EPOCHS
        ).fetchall()
    assert rows == [(2, False)]
    assert _count(RECEIPTS) == 2
    with pytest.raises(GrantProjectionConflict):
        f.project(f.token(grant_version=1))
    assert (_count(EPOCHS), _count(RECEIPTS)) == (1, 2)
    # A newly signed *higher* grant epoch may explicitly restore a grant.
    assert f.project(f.token(grant_version=3, allowed=True, revoked=False))
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT grant_version,enabled FROM " + EPOCHS
        ).fetchone() == (3, True)
    assert _count(RECEIPTS) == 3


@pytest.mark.parametrize("changes", [
    {"iss": "impostor"}, {"aud": "client-api"},
    {"kind": "organization.command"}, {"grant_version": True},
    {"grant_version": 0}, {"target_id": "not-uuid"},
    {"command_nonce": str(uuid4()).upper()},
    {"challenge": "unknown"}, {"request_digest": "Z" * 64},
    {"action": "organization.untrusted.doanything"},
    {"allowed": False, "revoked": False},
    {"allowed": True, "revoked": True},
    {"exp": 1}, {"iat": 99999999999},
])
def test_no_unsigned_weak_malformed_or_stale_decision_is_provisioned(changes):
    f = ProjectionFixture()
    with pytest.raises(PermissionDenied):
        f.project(f.token(**changes))
    assert (_count(RECEIPTS), _count(EPOCHS)) == (0, 0)


def test_mismatched_signer_forged_payload_and_untrusted_kid_cannot_write():
    f = ProjectionFixture()
    other = Ed25519PrivateKey.generate()
    for signed in (
        _sign(other, f.claims()),
        _sign(f.private, f.claims(), header={
            "alg": "none", "typ": "JWT", "kid": "ephemeral-decision",
        }),
        _sign(f.private, f.claims(), header={
            "alg": "EdDSA", "typ": "JWT", "kid": "untrusted",
        }),
    ):
        with pytest.raises(PermissionDenied):
            f.project(signed)
    signed = f.token()
    header, payload, sig = signed.split(".")
    replacement = f.claims(sub="forged")
    tampered = ".".join((
        header, _b64(json.dumps(replacement).encode()), sig,
    ))
    with pytest.raises(PermissionDenied):
        f.project(tampered)
    assert (_count(RECEIPTS), _count(EPOCHS)) == (0, 0)


def test_nonce_and_challenge_collision_not_projected_or_rewritten():
    f = ProjectionFixture()
    signed_claims = f.claims()
    signed = _sign(f.private, signed_claims)
    assert f.project(signed)
    for changes in (
        {"challenge": str(uuid4()), "command_nonce": signed_claims["command_nonce"]},
        {"challenge": signed_claims["challenge"], "command_nonce": str(uuid4())},
    ):
        forged_replay = _sign(
            f.private, {**signed_claims, **changes, "grant_version": 2},
        )
        with pytest.raises(GrantProjectionConflict):
            f.project(forged_replay)
    assert (_count(RECEIPTS), _count(EPOCHS)) == (1, 1)


def test_same_version_or_scope_change_is_denied_without_partial_receipt():
    f = ProjectionFixture()
    assert f.project(f.token())
    for event in (
        f.token(), f.token(grant_version=1),
        f.token(grant_version=2, sub="other-actor"),
        f.token(grant_version=2, target_id=str(uuid4())),
        f.token(grant_version=2, action="organization.membership.assign"),
    ):
        # Same-key duplicate JWS is an idempotent no-op; all new events must
        # have a strictly higher grant version with exactly the same scope.
        if f.project(event) is False:
            continue
        pytest.fail("Unexpected grant revision was applied")
    assert (_count(RECEIPTS), _count(EPOCHS)) == (1, 1)


def test_projection_requires_owner_privilege_and_receipts_are_immutable():
    f = ProjectionFixture()
    signed = f.token()
    for dsn in (RUNTIME, NONCE, COMPANY, REGISTRY):
        untrusted = PostgresVerifiedIamGrantProjector(
            owner_dsn=dsn, verifier=f.verifier,
        )
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            untrusted.project(signed, at=f.now)
    assert (_count(RECEIPTS), _count(EPOCHS)) == (0, 0)
    assert f.project(signed)
    with pytest.raises(psycopg.Error):
        with psycopg.connect(ADMIN) as owner:
            owner.execute(
                "UPDATE " + RECEIPTS + " SET decision_sha256=%s",
                ("b" * 64,),
            )


def test_out_of_window_expiry_is_invalid_even_with_valid_signature():
    f = ProjectionFixture()
    for seconds in (-5, 40):
        signed = f.token(exp=int(f.now.timestamp()) + seconds)
        with pytest.raises(PermissionDenied):
            f.project(signed)
    assert _count(RECEIPTS) == 0
