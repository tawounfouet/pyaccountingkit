"""G3-C02a Ed25519-pinned organization command authorization attestation.

Independent issuer signed the full command identity; this module contains only
PUBLIC verifying keys. Private signing keys / human sessions never belong in
the ordinary API worker or in the Python package.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ...application.organization_issuer_gateway import (
    CommandIdentity,
    VerifiedCommandEnvelope,
)
from ...application.service import PermissionDenied

_JWS_SEGMENT = re.compile(r"[A-Za-z0-9_-]+\Z")
_FIELDS = {
    "iss", "aud", "kind", "sub", "tenant_id", "action", "target_id",
    "request_id", "correlation_id", "request_digest", "iat", "nbf", "exp", "jti",
}


def _decode(segment: str) -> bytes:
    if not segment or not _JWS_SEGMENT.fullmatch(segment):
        raise ValueError("Noncanonical JWS segment")
    try:
        result = base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except (binascii.Error, ValueError) as error:
        raise ValueError("Invalid JWS segment") from error
    if base64.urlsafe_b64encode(result).rstrip(b"=").decode("ascii") != segment:
        raise ValueError("Ambiguous JWS encoding")
    return result


def _strict_dict(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicated signed claim")
        value[key] = item
    return value


def _json(data: bytes) -> dict[str, object]:
    result = json.loads(data.decode("utf-8"), object_pairs_hook=_strict_dict)
    if not isinstance(result, dict):
        raise ValueError("Signed JWS structure must be object")
    return result


def _text(data: dict[str, object], key: str) -> str:
    val = data.get(key)
    if not isinstance(val, str) or not val or val.strip() != val:
        raise ValueError("Invalid signed string claim")
    return val


def _epoch(data: dict[str, object], key: str) -> int:
    val = data.get(key)
    if type(val) is not int:
        raise ValueError("Invalid signed Unix epoch")
    return val


@dataclass(frozen=True, slots=True)
class OrganizationCommandTrust:
    """Pinned public verification material supplied only by trusted deployment."""

    issuer: str
    audience: str
    keys: Mapping[str, bytes]
    max_lifetime_seconds: int = 120
    max_skew_seconds: int = 0

    def __post_init__(self) -> None:
        if not self.issuer or not self.audience or not self.keys:
            raise ValueError("Pinned IAM issuer/audience/public keys required")
        if not 1 <= self.max_lifetime_seconds <= 300:
            raise ValueError("Short attestation TTL required")
        if not 0 <= self.max_skew_seconds <= 30:
            raise ValueError("Bounded clock skew required")
        copied = dict(self.keys)
        for kid, key in copied.items():
            if not isinstance(kid, str) or not kid or not isinstance(key, bytes):
                raise ValueError("Invalid trusted signing key")
            if len(key) != 32:
                raise ValueError("Ed25519 verification key requires 32 bytes")
            Ed25519PublicKey.from_public_bytes(key)
        object.__setattr__(self, "keys", MappingProxyType(copied))


class PinnedOrganizationCommandVerifier:
    """Exact claims + Ed25519 signature, pinned audience/issuer, short TTL."""

    def __init__(self, trust: OrganizationCommandTrust) -> None:
        if not isinstance(trust, OrganizationCommandTrust):
            raise ValueError("Explicit pinned command trust required")
        self._trust = trust

    def verify(self, token: str, *, at: datetime) -> VerifiedCommandEnvelope:
        try:
            if (
                not isinstance(token, str) or len(token.encode("utf-8")) > 8192
                or type(at) is not datetime or at.utcoffset() is None
            ):
                raise ValueError("Invalid signed token or verification clock")
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Expected three-part JWS")
            protected, payload, signature = parts
            header = _json(_decode(protected))
            if set(header) != {"alg", "typ", "kid"}:
                raise ValueError("Unexpected JWT header keys")
            if header["alg"] != "EdDSA" or header["typ"] != "JWT":
                raise ValueError("Unsupported signing algorithm")
            kid = _text(header, "kid")
            key = self._trust.keys.get(kid)
            if key is None:
                raise ValueError("Untrusted signing key")
            Ed25519PublicKey.from_public_bytes(key).verify(
                _decode(signature), f"{protected}.{payload}".encode("ascii"),
            )
            claims = _json(_decode(payload))
            if set(claims) != _FIELDS:
                raise ValueError("Signed command claims mismatch")
            if (
                claims["iss"] != self._trust.issuer
                or claims["aud"] != self._trust.audience
                or claims["kind"] != "organization.command"
            ):
                raise ValueError("Invalid issuer/audience/evidence purpose")
            issued = _epoch(claims, "iat")
            not_before = _epoch(claims, "nbf")
            expiry = _epoch(claims, "exp")
            if not (
                issued <= not_before <= expiry
                and 0 < expiry - issued <= self._trust.max_lifetime_seconds
            ):
                raise ValueError("Invalid attestation validity interval")
            epoch = at.astimezone(UTC).timestamp()
            skew = self._trust.max_skew_seconds
            if issued > epoch + skew or not_before > epoch + skew or epoch >= expiry + skew:
                raise ValueError("Expired/future-dated command attestation")
            digest = _text(claims, "request_digest")
            if not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ValueError("Noncanonical signed payload digest")
            envelope = VerifiedCommandEnvelope(
                issuer=_text(claims, "iss"),
                actor_id=_text(claims, "sub"),
                identity=CommandIdentity(
                    action=_text(claims, "action"),
                    tenant_id=_text(claims, "tenant_id"),
                    target_id=UUID(_text(claims, "target_id")),
                    request_id=_text(claims, "request_id"),
                    correlation_id=_text(claims, "correlation_id"),
                    digest=digest,
                ),
                nonce=UUID(_text(claims, "jti")),
                expires_at=datetime.fromtimestamp(expiry, tz=UTC),
            )
            return envelope
        except (
            ValueError, TypeError, KeyError, UnicodeError, binascii.Error,
            InvalidSignature, OverflowError,
        ) as error:
            raise PermissionDenied("Untrusted signed organization command") from error
