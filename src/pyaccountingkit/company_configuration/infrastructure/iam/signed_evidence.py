"""Pinned-key Ed25519 signed evidence adapters for privileged IAM ports.

Offline JWS verification is not a live IdP session, revocation source, or an
externally authorized grant decision. The approval source must remain trusted.
"""

import base64
import binascii
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Protocol
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ...application.privileged_operations import (
    PrivilegedAccessDenied,
    VerifiedApproval,
    VerifiedOperator,
)

_SEGMENT = re.compile(r"[A-Za-z0-9_-]+\Z")
_MAX_TOKEN_BYTES = 8192
_ALLOWED_HEADER = {"alg", "typ", "kid"}
_OPERATOR_FIELDS = {"iss", "aud", "kind", "sub", "tenant_id", "iat", "nbf", "exp", "jti"}
_APPROVAL_FIELDS = _OPERATOR_FIELDS | {
    "approval_id", "request_id", "login_role", "operation", "issued_at", "expires_at"
}
_REVOCATION_FIELDS = _OPERATOR_FIELDS | {"request_id", "login_role", "operation"}
_RECOVERY_APPROVAL_FIELDS = _OPERATOR_FIELDS | {
    "approval_id", "event_id", "request_id", "evidence_reference",
    "reason_code", "issued_at", "expires_at",
}


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicated signed JSON field")
        result[key] = value
    return result


def _decode(segment: str) -> bytes:
    if not segment or not _SEGMENT.fullmatch(segment):
        raise ValueError("Noncanonical JWS segment")
    decoded = base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    if base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") != segment:
        raise ValueError("Noncanonical JWS encoding")
    return decoded


def _json_object(value: bytes) -> dict[str, object]:
    parsed = json.loads(value.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
    if not isinstance(parsed, dict):
        raise ValueError("Signed envelope must be an object")
    return parsed


def _claim_string(claims: dict[str, object], key: str) -> str:
    value = claims.get(key)
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError("Missing or noncanonical signed claim")
    return value


def _claim_int(claims: dict[str, object], key: str) -> int:
    value = claims.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Signed time must be integer Unix seconds")
    return value


@dataclass(frozen=True, slots=True)
class SignedEvidenceTrust:
    """Pinned public keys from a trusted deployment configuration, not a token."""

    issuer: str
    audience: str
    keys: Mapping[str, bytes]
    kind: str
    max_lifetime_seconds: int = 300
    clock_skew_seconds: int = 0

    def __post_init__(self) -> None:
        if self.kind not in ("operator", "approval", "revocation", "recovery_approval"):
            raise ValueError("Explicit evidence kind required")
        if not self.issuer or not self.audience or not self.keys:
            raise ValueError("Pinned issuer, audience and keys required")
        if not 1 <= self.max_lifetime_seconds <= 600:
            raise ValueError("Bounded signed-evidence lifetime required")
        if not 0 <= self.clock_skew_seconds <= 30:
            raise ValueError("Clock skew must be tightly bounded")
        pinned = dict(self.keys)
        for kid, key in pinned.items():
            if not isinstance(kid, str) or not kid or not isinstance(key, bytes):
                raise ValueError("Canonical key IDs and public keys required")
            if len(key) != 32:
                raise ValueError("Ed25519 public keys must be 32 bytes")
            Ed25519PublicKey.from_public_bytes(key)
        object.__setattr__(self, "keys", MappingProxyType(pinned))


class TrustedApprovalEvidenceSource(Protocol):
    """Separate trusted store/client, NOT caller-provided approval JWS."""

    def read(self, reference: str) -> str: ...


class PinnedSignedEvidenceVerifier:
    """Rejects unsigned, algorithm-switched, expired or replay-ambiguous envelopes."""

    def __init__(self, trust: SignedEvidenceTrust) -> None:
        if not isinstance(trust, SignedEvidenceTrust):
            raise ValueError("Pinned trusted key material required")
        self._trust = trust

    def verify(self, token: str, *, at: datetime | None = None) -> dict[str, object]:
        try:
            if not isinstance(token, str) or len(token.encode()) > _MAX_TOKEN_BYTES:
                raise ValueError("Missing or oversized signed evidence")
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Three-part compact JWS required")
            header, payload, signature = parts
            h = _json_object(_decode(header))
            if set(h) != _ALLOWED_HEADER or h["typ"] != "JWT" or h["alg"] != "EdDSA":
                raise ValueError("Invalid JWS protected header")
            kid = _claim_string(h, "kid")
            public = self._trust.keys.get(kid)
            if public is None:
                raise ValueError("Untrusted signing key identifier")
            Ed25519PublicKey.from_public_bytes(public).verify(
                _decode(signature), f"{header}.{payload}".encode("ascii")
            )
            claims = _json_object(_decode(payload))
            accepted = {
                "operator": _OPERATOR_FIELDS,
                "approval": _APPROVAL_FIELDS,
                "revocation": _REVOCATION_FIELDS,
                "recovery_approval": _RECOVERY_APPROVAL_FIELDS,
            }[self._trust.kind]
            if set(claims) != accepted:
                raise ValueError("Unexpected signed claims")
            if (
                claims["iss"] != self._trust.issuer
                or claims["aud"] != self._trust.audience
                or claims["kind"] != self._trust.kind
            ):
                raise ValueError("Issuer, audience or evidence kind mismatch")
            _claim_string(claims, "sub")
            _claim_string(claims, "tenant_id")
            UUID(_claim_string(claims, "jti"))
            issued, not_before, expiry = (
                _claim_int(claims, "iat"), _claim_int(claims, "nbf"),
                _claim_int(claims, "exp"),
            )
            if not issued <= not_before <= expiry:
                raise ValueError("Incoherent signed time interval")
            if expiry - issued > self._trust.max_lifetime_seconds:
                raise ValueError("Excessive signed evidence lifetime")
            now = at if at is not None else datetime.now(UTC)
            if now.tzinfo is None or now.utcoffset() is None:
                raise ValueError("Timezone-aware verification clock required")
            epoch = now.timestamp()
            skew = self._trust.clock_skew_seconds
            if issued > epoch + skew or not_before > epoch + skew or epoch >= expiry + skew:
                raise ValueError("Evidence expired or not yet active")
            return claims
        except (
            ValueError, TypeError, UnicodeError, binascii.Error, InvalidSignature, OverflowError
        ) as exc:
            raise PrivilegedAccessDenied("Invalid signed IAM evidence") from exc


class SignedOperatorIdentity:
    """OperatorIdentityPort: authenticate transport evidence with pinned public key."""

    def __init__(self, verifier: PinnedSignedEvidenceVerifier) -> None:
        if verifier._trust.kind != "operator":
            raise ValueError("Operator signing trust root required")
        self._verifier = verifier

    def verify(self, context: object) -> VerifiedOperator:
        if not isinstance(context, str):
            raise PrivilegedAccessDenied("Compact signed operator assertion required")
        claims = self._verifier.verify(context)
        return VerifiedOperator(
            _claim_string(claims, "sub"), _claim_string(claims, "tenant_id")
        )


class SignedApprovalVerifier:
    """ApprovalVerificationPort: read signed evidence from a trusted separate source."""

    def __init__(
        self, verifier: PinnedSignedEvidenceVerifier, source: TrustedApprovalEvidenceSource,
    ) -> None:
        if verifier._trust.kind != "approval":
            raise ValueError("Distinct approval signing trust root required")
        if not callable(getattr(source, "read", None)):
            raise ValueError("Trusted approval evidence source required")
        self._verifier = verifier
        self._source = source

    def resolve(self, *, reference: str) -> VerifiedApproval:
        if not isinstance(reference, str) or not reference or len(reference) > 256:
            raise PrivilegedAccessDenied("Canonical approval reference required")
        try:
            token = self._source.read(reference)
        except Exception as exc:
            raise PrivilegedAccessDenied("Approval source unavailable") from exc
        claims = self._verifier.verify(token)
        try:
            if _claim_string(claims, "approval_id") != reference:
                raise ValueError("Approval reference substitution")
            request_id = UUID(_claim_string(claims, "request_id"))
            op = _claim_string(claims, "operation")
            if op not in ("rotate", "revoke"):
                raise ValueError("Unsupported privileged operation")
            signed_issued = _claim_int(claims, "issued_at")
            signed_expires = _claim_int(claims, "expires_at")
            if signed_issued > signed_expires or signed_expires > _claim_int(claims, "exp"):
                raise ValueError("Approval TTL inconsistent with signed envelope")
            return VerifiedApproval(
                reference, _claim_string(claims, "sub"), request_id,
                _claim_string(claims, "tenant_id"), _claim_string(claims, "login_role"),
                op, datetime.fromtimestamp(signed_issued, UTC),
                datetime.fromtimestamp(signed_expires, UTC),
            )
        except (ValueError, TypeError, OverflowError) as exc:
            raise PrivilegedAccessDenied("Invalid signed IAM approval") from exc
