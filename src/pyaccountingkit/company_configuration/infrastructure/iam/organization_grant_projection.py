"""G3-C02b3b2b1: independently re-verify signed IAM decision at owner boundary.

A signed upstream decision, not a caller-created Python reference, is mandatory.
The SQL owner/provisioning credential MUST NOT be available to normal app or
gateway SQL issuer deployments. CI uses an ephemeral Ed25519 test signer only.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import psycopg
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ...application.organization_issuer_gateway import ACTIONS
from ...application.service import PermissionDenied
from .organization_live_grants import (
    _FIELDS,
    SignedLiveGrantTrust,
    _canonical,
    _int,
    _object,
    _text,
)


class GrantProjectionConflict(ValueError):
    """A signed event is replayed inconsistently or its grant epoch is stale."""


@dataclass(frozen=True, slots=True)
class SignedIamGrantSnapshot:
    """Decoded cryptographic decision facts; NOT independently constructible proof."""

    authority_issuer: str
    signing_key_id: str
    grant_id: UUID
    grant_version: int
    actor_id: str
    tenant_id: str
    action: str
    target_id: UUID
    command_issuer: str
    request_id: str
    correlation_id: str
    request_digest: str
    command_nonce: UUID
    challenge: UUID
    allowed: bool
    revoked: bool
    issued_at: datetime
    expires_at: datetime
    decision_sha256: str


def _uuid(value: str) -> UUID:
    parsed = UUID(value)
    if str(parsed) != value:
        raise ValueError("Noncanonical IAM UUID")
    return parsed


class PinnedIamGrantProjectionVerifier:
    """Reverify the raw JWS with the independently pinned IAM decision key."""

    def __init__(self, trust: SignedLiveGrantTrust) -> None:
        if type(trust) is not SignedLiveGrantTrust:
            raise ValueError("Pinned IAM decision trust required for owner projection")
        self._trust = trust

    def verify(self, signed_decision: str, *, at: datetime) -> SignedIamGrantSnapshot:
        try:
            if not isinstance(signed_decision, str) or len(signed_decision) > 8192:
                raise ValueError("Bounded compact signed IAM decision required")
            if not isinstance(at, datetime) or at.utcoffset() is None:
                raise ValueError("Trusted timezone-aware verification clock required")
            segments = signed_decision.split(".")
            if len(segments) != 3:
                raise ValueError("Compact Ed25519 JWS required")
            header_enc, claims_enc, signature_enc = segments
            header = _object(_canonical(header_enc))
            if set(header) != {"alg", "typ", "kid"}:
                raise ValueError("Unexpected IAM signing header")
            if header["alg"] != "EdDSA" or header["typ"] != "JWT":
                raise ValueError("Invalid IAM decision signature algorithm")
            kid = _text(header, "kid")
            key = self._trust.keys.get(kid)
            if key is None:
                raise ValueError("Unknown independent IAM signing key")
            Ed25519PublicKey.from_public_bytes(key).verify(
                _canonical(signature_enc),
                f"{header_enc}.{claims_enc}".encode("ascii"),
            )
            claims = _object(_canonical(claims_enc))
            if set(claims) != _FIELDS:
                raise ValueError("Unexpected signed IAM decision fields")
            if (
                claims["iss"] != self._trust.issuer
                or claims["aud"] != self._trust.audience
                or claims["kind"] != "organization.authorization.decision"
            ):
                raise ValueError("Wrong independent IAM signer/audience/purpose")
            action = _text(claims, "action")
            if action not in ACTIONS.values():
                raise ValueError("Not an allowed typed organization action")
            grant_id = _uuid(_text(claims, "grant_id"))
            target = _uuid(_text(claims, "target_id"))
            nonce = _uuid(_text(claims, "command_nonce"))
            challenge = _uuid(_text(claims, "challenge"))
            for name in (
                "command_issuer", "sub", "tenant_id", "request_id",
                "correlation_id",
            ):
                _text(claims, name)
            digest = _text(claims, "request_digest")
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("Canonical command digest required")
            version = _int(claims, "grant_version")
            iat, nbf, exp = (_int(claims, f) for f in ("iat", "nbf", "exp"))
            if version < 1 or not (
                iat <= nbf < exp and
                0 < exp - iat <= self._trust.max_lifetime_seconds
            ):
                raise ValueError("Invalid IAM grant revision/timing")
            seconds = at.astimezone(UTC).timestamp()
            skew = self._trust.clock_skew_seconds
            if iat > seconds + skew or nbf > seconds + skew or seconds >= exp + skew:
                raise ValueError("Stale/future signed IAM grant decision")
            allowed, revoked = claims["allowed"], claims["revoked"]
            if type(allowed) is not bool or type(revoked) is not bool or (
                (allowed, revoked) not in ((True, False), (False, True))
            ):
                raise ValueError("Only positive grant or explicit revocation projects")
            return SignedIamGrantSnapshot(
                authority_issuer=self._trust.issuer, signing_key_id=kid,
                grant_id=grant_id, grant_version=version,
                actor_id=_text(claims, "sub"),
                tenant_id=_text(claims, "tenant_id"), action=action,
                target_id=target,
                command_issuer=_text(claims, "command_issuer"),
                request_id=_text(claims, "request_id"),
                correlation_id=_text(claims, "correlation_id"),
                request_digest=digest, command_nonce=nonce,
                challenge=challenge, allowed=allowed, revoked=revoked,
                issued_at=datetime.fromtimestamp(iat, UTC),
                expires_at=datetime.fromtimestamp(exp, UTC),
                decision_sha256=hashlib.sha256(signed_decision.encode("ascii")).hexdigest(),
            )
        except Exception as exc:
            # Never leak raw token or secret in application errors.
            raise PermissionDenied("Independent IAM signed grant projection denied") from exc


class PostgresVerifiedIamGrantProjector:
    """Verify the SIGNED JWS then atomically project grant + immutable receipt.

    The DSN must belong to a separately managed privileged IAM projection
    identity, NOT an ordinary API/gateway SQL issuer. No background worker is
    launched by this synchronous adapter; transport/outbox are separate.
    """

    def __init__(
        self, *, owner_dsn: str, verifier: PinnedIamGrantProjectionVerifier,
    ) -> None:
        if not isinstance(owner_dsn, str) or not owner_dsn.strip():
            raise ValueError("Independent SQL projection owner credential required")
        if type(verifier) is not PinnedIamGrantProjectionVerifier:
            raise ValueError("Raw IAM JWS verifier mandatory at owner boundary")
        self._dsn = owner_dsn
        self._verifier = verifier

    def __repr__(self) -> str:
        return "PostgresVerifiedIamGrantProjector(credentials=<redacted>)"

    def project(self, signed_decision: str, *, at: datetime) -> bool:
        """True for new projection, False for exact duplicate, fail-closed else.

        Duplicate and stale events do not advance grant epochs. The grant row
        and signed-evidence metadata receipt change in ONE SQL transaction.
        """
        snapshot = self._verifier.verify(signed_decision, at=at)
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(
                "INSERT INTO company_configuration.organization_actor_grant_decision_receipts "
                "(authority_issuer,challenge,command_nonce,tenant_id,grant_id,"
                "grant_version,actor_id,action,target_id,command_issuer,"
                "request_id,correlation_id,request_digest,decision_sha256,"
                "signing_key_id,allowed,revoked,issued_at,expires_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT DO NOTHING RETURNING challenge",
                (
                    snapshot.authority_issuer, snapshot.challenge, snapshot.command_nonce,
                    snapshot.tenant_id, snapshot.grant_id, snapshot.grant_version,
                    snapshot.actor_id, snapshot.action, snapshot.target_id,
                    snapshot.command_issuer, snapshot.request_id,
                    snapshot.correlation_id, snapshot.request_digest,
                    snapshot.decision_sha256, snapshot.signing_key_id,
                    snapshot.allowed, snapshot.revoked, snapshot.issued_at,
                    snapshot.expires_at,
                ),
            ).fetchone()
            if row is None:
                duplicate = conn.execute(
                    "SELECT decision_sha256 FROM "
                    "company_configuration.organization_actor_grant_decision_receipts "
                    "WHERE (authority_issuer=%s AND challenge=%s) "
                    "OR (authority_issuer=%s AND command_nonce=%s)",
                    (
                        snapshot.authority_issuer, snapshot.challenge,
                        snapshot.authority_issuer, snapshot.command_nonce,
                    ),
                ).fetchall()
                if len(duplicate) == 1 and duplicate[0][0] == snapshot.decision_sha256:
                    return False
                raise GrantProjectionConflict("IAM event replay or nonce collision")
            current = conn.execute(
                "SELECT tenant_id,actor_id,action,target_id,authority_issuer,grant_version "
                "FROM company_configuration.organization_actor_grant_epochs "
                "WHERE grant_id=%s FOR UPDATE",
                (snapshot.grant_id,),
            ).fetchone()
            if current is None:
                conn.execute(
                    "INSERT INTO company_configuration.organization_actor_grant_epochs "
                    "(grant_id,tenant_id,actor_id,action,target_id,authority_issuer,"
                    "grant_version,enabled,valid_until,decision_sha256,source_event_id) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        snapshot.grant_id, snapshot.tenant_id, snapshot.actor_id,
                        snapshot.action, snapshot.target_id, snapshot.authority_issuer,
                        snapshot.grant_version, snapshot.allowed,
                        snapshot.expires_at, snapshot.decision_sha256, snapshot.challenge,
                    ),
                )
            else:
                expected = (
                    snapshot.tenant_id, snapshot.actor_id, snapshot.action,
                    snapshot.target_id, snapshot.authority_issuer,
                )
                if current[:5] != expected or snapshot.grant_version <= current[5]:
                    raise GrantProjectionConflict("Stale IAM grant revision or immutable scope")
                conn.execute(
                    "UPDATE company_configuration.organization_actor_grant_epochs "
                    "SET grant_version=%s,enabled=%s,valid_until=%s,decision_sha256=%s,"
                    "source_event_id=%s,observed_at=clock_timestamp() WHERE grant_id=%s",
                    (
                        snapshot.grant_version, snapshot.allowed, snapshot.expires_at,
                        snapshot.decision_sha256, snapshot.challenge, snapshot.grant_id,
                    ),
                )
        return True
