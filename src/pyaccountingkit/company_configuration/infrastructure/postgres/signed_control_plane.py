"""L02-07i: fail-closed deployment checks and pinned-key IAM composition.

Validates intended deployment settings; DOES NOT create a network boundary or
fetch live IAM records. External approval source and current-grant policy must
be configured by a privileged, independently controlled deployment.
"""

import base64
import binascii
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import parse_qs, urlsplit

from ...application.privileged_operations import PrivilegedPolicyPort, TimePort
from ..iam.signed_evidence import (
    PinnedSignedEvidenceVerifier,
    SignedApprovalVerifier,
    SignedEvidenceTrust,
    SignedOperatorIdentity,
    TrustedApprovalEvidenceSource,
)


class UnsafeControlPlaneDeployment(ValueError):
    """Privileged application configuration violates a fail-closed assumption."""


_FORBIDDEN_KEYS = frozenset({
    "CC_PG_ADMIN_DSN", "PGPASSWORD", "DATABASE_URL", "CC_PG_DSN",
    "CC_PG_DSN_B", "CC_PG_DISPATCH_DSN", "CC_PG_INBOX_DSN",
    "CC_PG_UNBOUND_DSN", "CC_PG_DISPATCH_DSN_B", "CC_PG_INBOX_DSN_B",
})
_ALLOWED_DSN_PARAMS = frozenset({
    "sslmode", "sslrootcert", "application_name", "connect_timeout",
    "target_session_attrs",
})


def _guard_dsn(value: str, *, expected: str) -> None:
    try:
        u = urlsplit(value)
        if u.scheme not in ("postgresql", "postgres"):
            raise ValueError("Unsupported PostgreSQL URI scheme")
        if u.username != expected or not u.password or not u.hostname:
            raise ValueError("Incorrect dedicated PostgreSQL login")
        if u.hostname.lower() in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Production isolation requires a nonlocal DB endpoint")
        if not u.path or u.path == "/" or u.fragment:
            raise ValueError("Explicit database and no URI fragment required")
        query = parse_qs(u.query, keep_blank_values=True, strict_parsing=True)
        if not set(query).issubset(_ALLOWED_DSN_PARAMS):
            raise ValueError("Unexpected PostgreSQL connection options")
        if query.get("sslmode") != ["verify-full"]:
            raise ValueError("Verified TLS hostname and CA required")
        if u.port is not None and not 1 <= u.port <= 65535:
            raise ValueError("Invalid port")
    except (ValueError, AttributeError, TypeError) as exc:
        raise UnsafeControlPlaneDeployment("Unsafe privileged PostgreSQL DSN") from exc


def _key(encoded: str) -> bytes:
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) != 32:
            raise ValueError("Invalid public-key size")
        return raw
    except (ValueError, TypeError, binascii.Error) as exc:
        raise UnsafeControlPlaneDeployment("Expected pinned Ed25519 public key") from exc


@dataclass(frozen=True, slots=True, repr=False)
class SignedControlPlaneSettings:
    audit_writer_dsn: str
    control_plane_dsn: str
    operator_trust: SignedEvidenceTrust
    approval_trust: SignedEvidenceTrust

    def __repr__(self) -> str:
        return "SignedControlPlaneSettings(credentials=<redacted>, trust=pinned)"

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> "SignedControlPlaneSettings":
        if any(key in env for key in _FORBIDDEN_KEYS):
            raise UnsafeControlPlaneDeployment("Forbidden privileged or runtime credentials")
        # Never import the live process environment implicitly here.
        try:
            control = env["CC_PG_CONTROL_PLANE_DSN"]
            audit = env["CC_PG_PRIVILEGED_AUDIT_DSN"]
            issuer_op = env["CC_IAM_OPERATOR_ISSUER"]
            issuer_ap = env["CC_IAM_APPROVAL_ISSUER"]
            audience = env["CC_IAM_AUDIENCE"]
            kid_op = env["CC_IAM_OPERATOR_KID"]
            kid_ap = env["CC_IAM_APPROVAL_KID"]
            key_op = env["CC_IAM_OPERATOR_ED25519_PUBLIC_B64"]
            key_ap = env["CC_IAM_APPROVAL_ED25519_PUBLIC_B64"]
        except (KeyError, TypeError) as exc:
            raise UnsafeControlPlaneDeployment("Missing explicit privileged setting") from exc
        _guard_dsn(control, expected="cc_control_plane")
        _guard_dsn(audit, expected="cc_privileged_audit")
        if (
            control == audit or issuer_op == issuer_ap or kid_op == kid_ap
            or key_op == key_ap
        ):
            raise UnsafeControlPlaneDeployment("Separate IAM trust domains required")
        if not issuer_op or not issuer_ap or not audience or not kid_op or not kid_ap:
            raise UnsafeControlPlaneDeployment("Explicit nonempty IAM trust required")
        return cls(
            audit, control,
            SignedEvidenceTrust(issuer_op, audience, {kid_op: _key(key_op)}, "operator"),
            SignedEvidenceTrust(issuer_ap, audience, {kid_ap: _key(key_ap)}, "approval"),
        )


def build_signed_restricted_privileged_service(
    *, settings: SignedControlPlaneSettings,
    approval_source: TrustedApprovalEvidenceSource,
    policy: PrivilegedPolicyPort,
    clock: TimePort,
):
    """Compose verified JWS ports with restricted SQL capabilities.

    The approval_source MUST be a trusted, independently operated repository;
    accepting user-provided approval JWS tokens as its source is insecure.
    The policy MUST consult live authoritative grants and revocations.
    """
    if not isinstance(settings, SignedControlPlaneSettings):
        raise UnsafeControlPlaneDeployment("Validated privileged configuration required")
    from .restricted_control_plane import build_restricted_privileged_service

    return build_restricted_privileged_service(
        audit_writer_dsn=settings.audit_writer_dsn,
        control_plane_dsn=settings.control_plane_dsn,
        identity=SignedOperatorIdentity(PinnedSignedEvidenceVerifier(settings.operator_trust)),
        approvals=SignedApprovalVerifier(
            PinnedSignedEvidenceVerifier(settings.approval_trust), approval_source
        ),
        policy=policy, clock=clock,
    )
