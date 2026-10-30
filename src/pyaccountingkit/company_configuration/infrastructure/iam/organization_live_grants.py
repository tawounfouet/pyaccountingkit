"""G3-C02b2 live, signed IAM decision adapter for the isolated L03 gateway.

One HTTPS request per command; request-specific random challenge and signed
Ed25519 response. No positive cache, local allowlist, or caller-issued grant.
A reachable test HTTP stub is NOT a production IAM integration attestation.
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
from typing import Protocol
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from ...application.ports import TrustedPrincipal
from ...application.service import PermissionDenied
from .http_revocation_source import HttpsIamTransport, IamHttpTransport

_SEGMENT = re.compile(r"[A-Za-z0-9_-]+\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_FIELDS = {
    "iss", "aud", "kind", "command_issuer", "sub", "tenant_id",
    "action", "target_id", "request_id", "correlation_id", "request_digest",
    "command_nonce", "challenge", "allowed", "revoked", "grant_id",
    "grant_version", "iat", "nbf", "exp",
}
_MAX_RESPONSE_BYTES = 8192


def _canonical(segment: str) -> bytes:
    if not isinstance(segment, str) or not segment or not _SEGMENT.fullmatch(segment):
        raise ValueError("Noncanonical signed IAM segment")
    try:
        decoded = base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid signed IAM segment") from exc
    if base64.urlsafe_b64encode(decoded).rstrip(b"=").decode() != segment:
        raise ValueError("Ambiguous signed IAM encoding")
    return decoded


def _unique_dict(pairs: list[tuple[str, object]]) -> dict[str, object]:
    data: dict[str, object] = {}
    for key, value in pairs:
        if key in data:
            raise ValueError("Duplicated signed IAM field")
        data[key] = value
    return data


def _object(data: bytes) -> dict[str, object]:
    parsed = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_dict)
    if not isinstance(parsed, dict):
        raise ValueError("Signed IAM evidence must be an object")
    return parsed


def _text(claims: Mapping[str, object], name: str) -> str:
    value = claims.get(name)
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError("Noncanonical signed IAM field")
    return value


def _int(claims: Mapping[str, object], name: str) -> int:
    value = claims.get(name)
    if type(value) is not int:
        raise ValueError("Signed IAM timestamp/version must be an integer")
    return value


@dataclass(frozen=True, slots=True)
class SignedLiveGrantTrust:
    """Independently configured IAM *decision* authority, not command token key."""

    issuer: str
    audience: str
    keys: Mapping[str, bytes]
    max_lifetime_seconds: int = 30
    clock_skew_seconds: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.issuer, str) or not self.issuer.strip():
            raise ValueError("Trusted IAM decision issuer required")
        if not isinstance(self.audience, str) or not self.audience.strip():
            raise ValueError("Trusted gateway decision audience required")
        if not 1 <= self.max_lifetime_seconds <= 60:
            raise ValueError("Short signed IAM decision lifetime required")
        if not 0 <= self.clock_skew_seconds <= 15:
            raise ValueError("Tightly bounded IAM clock skew required")
        if not self.keys:
            raise ValueError("Pinned public decision verification keys required")
        cloned = dict(self.keys)
        for kid, key in cloned.items():
            if (
                not isinstance(kid, str) or not kid or kid != kid.strip()
                or type(key) is not bytes or len(key) != 32
            ):
                raise ValueError("Canonical Ed25519 IAM decision key required")
            Ed25519PublicKey.from_public_bytes(key)
        object.__setattr__(self, "keys", MappingProxyType(cloned))


class LiveGrantClock(Protocol):
    def now(self) -> datetime: ...


class UtcLiveGrantClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class HttpsSignedOrganizationGrantSource:
    """Fresh POST + independently signed IAM allow/deny/revoked decision.

    Service bearer credential and pinned HTTPS origin are injected by a
    separately configured gateway secret provider. Neither raw command JWT
    nor signing private keys are sent to the authorization endpoint.

    The authorization provider must validate both its gateway service
    credential and the scoped actor's *current* grant/revocation state.
    """

    def __init__(
        self, *, origin: str, service_token: str, trust: SignedLiveGrantTrust,
        timeout: float = 3.0, transport: IamHttpTransport | None = None,
        clock: LiveGrantClock | None = None,
    ) -> None:
        try:
            url = urlsplit(origin)
        except ValueError as exc:
            raise ValueError("Pinned HTTPS IAM origin required") from exc
        if (
            not isinstance(origin, str) or url.scheme != "https"
            or not url.hostname or url.path not in ("", "/")
            or url.query or url.fragment or url.username or url.password
            or "\\" in origin
            or url.hostname in ("localhost", "127.0.0.1", "::1")
        ):
            raise ValueError("Independent pinned HTTPS IAM origin required")
        if (
            not isinstance(service_token, str) or not service_token.strip()
            or any(x in service_token for x in ("\n", "\r"))
        ):
            raise ValueError("Trusted gateway IAM service credential required")
        if type(trust) is not SignedLiveGrantTrust:
            raise ValueError("Pinned IAM signed decision trust required")
        if not 0.1 <= timeout <= 5.0:
            raise ValueError("Bounded IAM authorization timeout required")
        self._url = origin.rstrip("/") + "/v1/organization/authorization/decisions"
        self._credential = service_token
        self._trust = trust
        self._timeout = timeout
        self._transport = transport if transport is not None else HttpsIamTransport()
        self._clock = clock if clock is not None else UtcLiveGrantClock()

    def __repr__(self) -> str:
        return "HttpsSignedOrganizationGrantSource(credentials=<redacted>)"

    def require(
        self, *, issuer: str, principal: TrustedPrincipal, action: str,
        target_id: UUID, request_id: str, correlation_id: str,
        request_digest: str, command_nonce: UUID,
    ) -> None:
        try:
            if (
                not isinstance(principal, TrustedPrincipal)
                or type(target_id) is not UUID or type(command_nonce) is not UUID
                or not _DIGEST.fullmatch(request_digest)
            ):
                raise ValueError("Typed IAM command context required")
            for value in (issuer, action, request_id, correlation_id):
                if not isinstance(value, str) or not value or value != value.strip():
                    raise ValueError("Canonical IAM command context required")
            now = self._clock.now()
            if not isinstance(now, datetime) or now.utcoffset() is None:
                raise ValueError("Trusted timezone-aware grant verification clock required")
            now = now.astimezone(UTC)
            # A new unpredictable challenge prevents old signed allow decisions
            # from being transplanted to a later independent POST.
            challenge = uuid4()
            expected = {
                "command_issuer": issuer, "sub": principal.actor_id,
                "tenant_id": principal.tenant_id, "action": action,
                "target_id": str(target_id), "request_id": request_id,
                "correlation_id": correlation_id, "request_digest": request_digest,
                "command_nonce": str(command_nonce), "challenge": str(challenge),
            }
            body = json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()
            response = self._transport.request(
                "POST", self._url,
                {
                    "Authorization": "Bearer " + self._credential,
                    "Content-Type": "application/json",
                    "Accept": "application/jose",
                    "Cache-Control": "no-store",
                },
                body, self._timeout,
            )
            if (
                response.status != 200 or response.content_type != "application/jose"
                or not 1 <= len(response.body) <= _MAX_RESPONSE_BYTES
            ):
                raise ValueError("No authoritative signed IAM decision")
            parts = response.body.decode("ascii").split(".")
            if len(parts) != 3:
                raise ValueError("Compact Ed25519 decision required")
            header_enc, claims_enc, signature_enc = parts
            header = _object(_canonical(header_enc))
            if set(header) != {"alg", "typ", "kid"}:
                raise ValueError("Unexpected IAM signing header")
            if header["alg"] != "EdDSA" or header["typ"] != "JWT":
                raise ValueError("Unsigned or weak IAM decision")
            public_key = self._trust.keys.get(_text(header, "kid"))
            if public_key is None:
                raise ValueError("Untrusted IAM decision signing key")
            Ed25519PublicKey.from_public_bytes(public_key).verify(
                _canonical(signature_enc),
                f"{header_enc}.{claims_enc}".encode("ascii"),
            )
            decision = _object(_canonical(claims_enc))
            if set(decision) != _FIELDS:
                raise ValueError("Unexpected signed IAM grant fields")
            if (
                decision["iss"] != self._trust.issuer
                or decision["aud"] != self._trust.audience
                or decision["kind"] != "organization.authorization.decision"
            ):
                raise ValueError("Wrong signed IAM decision authority/audience")
            if any(decision.get(name) != value for name, value in expected.items()):
                raise ValueError("Signed IAM decision does not bind this command")
            if type(decision["allowed"]) is not bool or type(decision["revoked"]) is not bool:
                raise ValueError("Nonboolean signed IAM grant/revocation")
            if decision["allowed"] is not True or decision["revoked"] is not False:
                raise ValueError("Denied or revoked current IAM authorization")
            UUID(_text(decision, "grant_id"))
            if _int(decision, "grant_version") < 1:
                raise ValueError("Missing current IAM grant version")
            iat, nbf, exp = (_int(decision, field) for field in ("iat", "nbf", "exp"))
            if not (
                iat <= nbf < exp and 0 < exp - iat <= self._trust.max_lifetime_seconds
            ):
                raise ValueError("Invalid signed decision time range")
            seconds = now.timestamp()
            skew = self._trust.clock_skew_seconds
            if iat > seconds + skew or nbf > seconds + skew or seconds >= exp + skew:
                raise ValueError("Expired/future-dated IAM decision")
        except Exception as exc:
            # Do not expose HTTP response bodies, service credential, or JWS to
            # the ordinary caller. ANY inability to verify is a hard denial.
            raise PermissionDenied("Independent current IAM grant not verified") from exc
