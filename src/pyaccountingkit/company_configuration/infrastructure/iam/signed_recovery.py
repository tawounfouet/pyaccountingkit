"""Pinned independent Ed25519 recovery approval and restricted SQL composition.

A signed approval is NOT a live IAM grant, a delivery receipt, or a workload
attestation. Approval source and current policy must be independently trusted.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from ...application.iam_ack_recovery import (
    IamAckRecoveryService,
    RecoveryClockPort,
    RecoveryPolicyPort,
    VerifiedRedriveApproval,
)
from ...application.privileged_operations import PrivilegedAccessDenied
from .signed_evidence import (
    PinnedSignedEvidenceVerifier,
    SignedEvidenceTrust,
    SignedOperatorIdentity,
    TrustedApprovalEvidenceSource,
    _claim_int,
    _claim_string,
)


class SignedRecoveryApprovalVerifier:
    """Read a recovery approval from an independent source, not from a caller."""

    def __init__(
        self,
        verifier: PinnedSignedEvidenceVerifier,
        source: TrustedApprovalEvidenceSource,
    ) -> None:
        if verifier._trust.kind != "recovery_approval":
            raise ValueError("Dedicated recovery approval signing trust required")
        if not callable(getattr(source, "read", None)):
            raise ValueError("Independent recovery approval source required")
        self._verifier = verifier
        self._source = source

    def resolve(self, *, reference: str) -> VerifiedRedriveApproval:
        if (
            not isinstance(reference, str)
            or not reference or reference.strip() != reference or len(reference) > 128
        ):
            raise PrivilegedAccessDenied("Canonical recovery approval reference required")
        try:
            token = self._source.read(reference)
        except Exception as exc:
            raise PrivilegedAccessDenied("Recovery approval source unavailable") from exc
        claims = self._verifier.verify(token)
        try:
            if _claim_string(claims, "approval_id") != reference:
                raise ValueError("Recovery approval reference mismatch")
            issued = _claim_int(claims, "issued_at")
            expires = _claim_int(claims, "expires_at")
            if not _claim_int(claims, "iat") <= issued < expires <= _claim_int(claims, "exp"):
                raise ValueError("Recovery approval timestamps outside signed envelope")
            reason = _claim_string(claims, "reason_code")
            if reason not in (
                "PROVIDER_RECOVERED", "INCIDENT_REVIEWED", "DELIVERY_RESTORED"
            ):
                raise ValueError("Unsupported recovery decision")
            evidence = _claim_string(claims, "evidence_reference")
            if len(evidence) > 256:
                raise ValueError("Oversized recovery evidence reference")
            return VerifiedRedriveApproval(
                reference,
                _claim_string(claims, "sub"),
                UUID(_claim_string(claims, "event_id")),
                UUID(_claim_string(claims, "request_id")),
                _claim_string(claims, "tenant_id"),
                evidence,
                reason,
                datetime.fromtimestamp(issued, UTC),
                datetime.fromtimestamp(expires, UTC),
            )
        except (ValueError, TypeError, OverflowError) as exc:
            raise PrivilegedAccessDenied("Invalid signed recovery approval") from exc


@dataclass(frozen=True, slots=True, repr=False)
class SignedRecoverySettings:
    """Only pinned, separated trust roots and a dedicated recovery SQL login."""

    recovery_dsn: str
    operator_trust: SignedEvidenceTrust
    recovery_approval_trust: SignedEvidenceTrust

    def __repr__(self) -> str:
        return "SignedRecoverySettings(dsn=<redacted>, keys=pinned)"

    @classmethod
    def from_environment(cls, env: Mapping[str, str]) -> "SignedRecoverySettings":
        from ..postgres.signed_control_plane import (
            UnsafeControlPlaneDeployment,
            _FORBIDDEN_KEYS,
            _guard_dsn,
            _key,
        )

        disallowed = _FORBIDDEN_KEYS | {
            "CC_PG_CONTROL_PLANE_DSN", "CC_PG_PRIVILEGED_AUDIT_DSN",
            "CC_PG_IAM_DELIVERY_DSN", "CC_PG_IAM_REVOCATION_DSN",
        }
        if any(key in env for key in disallowed):
            raise UnsafeControlPlaneDeployment("Unrelated privileged SQL capability")
        try:
            dsn = env["CC_PG_IAM_RECOVERY_DSN"]
            audience = env["CC_IAM_AUDIENCE"]
            operator_issuer = env["CC_IAM_OPERATOR_ISSUER"]
            reviewer_issuer = env["CC_IAM_RECOVERY_APPROVAL_ISSUER"]
            operator_kid = env["CC_IAM_OPERATOR_KID"]
            reviewer_kid = env["CC_IAM_RECOVERY_APPROVAL_KID"]
            operator_key = env["CC_IAM_OPERATOR_ED25519_PUBLIC_B64"]
            reviewer_key = env["CC_IAM_RECOVERY_APPROVAL_ED25519_PUBLIC_B64"]
        except (KeyError, TypeError) as exc:
            raise UnsafeControlPlaneDeployment("Missing pinned recovery configuration") from exc
        _guard_dsn(dsn, expected="cc_iam_recovery")
        if (
            not audience or not operator_issuer or not reviewer_issuer
            or not operator_kid or not reviewer_kid
            or operator_issuer == reviewer_issuer
            or operator_key == reviewer_key
        ):
            raise UnsafeControlPlaneDeployment("Independent recovery trust roots required")
        return cls(
            dsn,
            SignedEvidenceTrust(
                operator_issuer, audience, {operator_kid: _key(operator_key)}, "operator"
            ),
            SignedEvidenceTrust(
                reviewer_issuer, audience, {reviewer_kid: _key(reviewer_key)},
                "recovery_approval",
            ),
        )


def require_recovery_sql_capabilities(dsn: str) -> None:
    """Live PostgreSQL least-privilege check; separate from network/TLS startup."""
    from ..postgres.restricted_control_plane import PrivilegedCompositionDenied

    import psycopg

    with psycopg.connect(dsn) as conn:
        identity = conn.execute(
            "SELECT session_user,rolsuper,rolcreaterole,rolcreatedb,rolbypassrls,"
            "rolreplication FROM pg_catalog.pg_roles WHERE rolname=session_user"
        ).fetchone()
        if identity != ("cc_iam_recovery", False, False, False, False, False):
            raise PrivilegedCompositionDenied("Recovery SQL login is privileged or foreign")
        grants = conn.execute(
            "SELECT "
            "has_function_privilege(session_user, "
            "'company_configuration.cp_redrive_dead_iam_ack("
            "uuid,uuid,text,text,text,text,text,text)','EXECUTE'),"
            "has_function_privilege(session_user, "
            "'company_configuration.cp_claim_iam_ack(integer)','EXECUTE'),"
            "has_function_privilege(session_user, "
            "'company_configuration.cp_execute_fence("
            "uuid,text,text,text,text,text,text)','EXECUTE'),"
            "has_table_privilege(session_user,"
            "'company_configuration.privileged_iam_ack_outbox','SELECT')"
        ).fetchone()
        if grants != (True, False, False, False):
            raise PrivilegedCompositionDenied("Recovery database capability mismatch")


def build_signed_restricted_recovery_service(
    *, settings: SignedRecoverySettings, approval_source: TrustedApprovalEvidenceSource,
    policy: RecoveryPolicyPort, clock: RecoveryClockPort,
) -> IamAckRecoveryService:
    """Verify SQL session capabilities, then wire signed AuthN/SoD ports.

    The external approval source must be trusted and current; this function does
    not authenticate its network origin or prove a protected workload exists.
    """
    if not isinstance(settings, SignedRecoverySettings):
        raise ValueError("Explicit validated recovery settings required")
    from ..postgres.iam_ack_operations import PostgresIamDeadAckRecovery
    from ..postgres.restricted_control_plane import PrivilegedCompositionDenied
    from ..postgres.signed_control_plane import _guard_dsn

    _guard_dsn(settings.recovery_dsn, expected="cc_iam_recovery")
    a, b = settings.operator_trust, settings.recovery_approval_trust
    if (
        a.kind != "operator" or b.kind != "recovery_approval"
        or a.audience != b.audience or a.issuer == b.issuer
        or set(a.keys.values()) & set(b.keys.values())
    ):
        raise PrivilegedCompositionDenied("Recovery signing trust separation invalid")
    require_recovery_sql_capabilities(settings.recovery_dsn)
    return IamAckRecoveryService(
        identity=SignedOperatorIdentity(PinnedSignedEvidenceVerifier(a)),
        approvals=SignedRecoveryApprovalVerifier(PinnedSignedEvidenceVerifier(b), approval_source),
        policy=policy,
        repository=PostgresIamDeadAckRecovery(settings.recovery_dsn),
        clock=clock,
    )
