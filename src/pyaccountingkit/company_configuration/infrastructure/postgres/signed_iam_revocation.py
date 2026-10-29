"""Signed IAM revocation consumer with durable PostgreSQL acknowledgement.

No remote IAM is connected by this class. Evidence must originate from a
trusted, separately operated signing authority; public keys are pinned by the
owner deployment. The narrow database login cannot mutate fences directly.
"""

import hashlib
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ...application.privileged_operations import PrivilegedAccessDenied
from ..iam.signed_evidence import PinnedSignedEvidenceVerifier, SignedEvidenceTrust


def _connect(dsn: str):
    # PostgreSQL is an optional dependency; pure unit consumers must still import.
    import psycopg

    return psycopg.connect(dsn)


class IAMRevocationAckPending(RuntimeError):
    """SQL receipt committed but external delivery acknowledgement failed."""


@dataclass(frozen=True, slots=True)
class IAMRevocationReceipt:
    revocation_id: UUID
    request_id: UUID
    status: str

    @property
    def enforced(self) -> bool:
        # ALREADY_REVOKED is not proof that *this* delivery caused revocation.
        return self.status == "APPLIED"


class TrustedIAMRevocationEventSource(Protocol):
    """External provider adapter owned by a separate IAM control plane.

    The real transport, credentials and current-provider authorization policy
    must be implemented and independently reviewed outside this test slice.
    """

    def poll(self, *, limit: int) -> tuple[str, ...]: ...

    def acknowledge(self, *, revocation_id: UUID, status: str) -> None: ...


class SignedIAMRevocationAcknowledger:
    """Verify exact signed event, then record SQL state and idempotent receipt."""

    def __init__(self, *, dsn: str, trust: SignedEvidenceTrust) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("Restricted revocation delivery SQL credential required")
        if not isinstance(trust, SignedEvidenceTrust) or trust.kind != "revocation":
            raise ValueError("Independent pinned IAM revocation signing root required")
        self._dsn = dsn
        self._verifier = PinnedSignedEvidenceVerifier(trust)

    def __repr__(self) -> str:
        return "SignedIAMRevocationAcknowledger(dsn=<redacted>, trust=pinned)"

    def apply(self, signed_event: str) -> IAMRevocationReceipt:
        claims = self._verifier.verify(signed_event)
        try:
            revocation_id = UUID(claims["jti"])
            request_id = UUID(claims["request_id"])
            tenant_id = claims["tenant_id"]
            login_role = claims["login_role"]
            operation = claims["operation"]
            approval_id = claims["approval_id"]
            revoker = claims["sub"]
            issued_at = claims["iat"]
            revoked_at = claims["revoked_at"]
            if (
                not all(
                    isinstance(value, str) and value and value.strip() == value
                    for value in (tenant_id, login_role, approval_id, revoker)
                )
                or operation not in ("rotate", "revoke")
                or type(revoked_at) is not int
                or not issued_at - 600 <= revoked_at <= issued_at
            ):
                raise ValueError("Revocation scope or time invalid")
        except (TypeError, ValueError, KeyError) as exc:
            raise PrivilegedAccessDenied("Invalid signed revocation event") from exc
        digest = hashlib.sha256(signed_event.encode("ascii")).hexdigest()
        with _connect(self._dsn) as conn:
            login = conn.execute("SELECT session_user").fetchone()[0]
            if login != "cc_iam_revocation":
                raise PrivilegedAccessDenied("Dedicated IAM revocation SQL login required")
            result = conn.execute(
                "SELECT company_configuration.cp_ack_iam_revocation("
                "%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    revocation_id, request_id, tenant_id, login_role,
                    operation, approval_id, revoker, digest,
                ),
            ).fetchone()[0]
        if result not in ("APPLIED", "ALREADY_REVOKED", "TOO_LATE"):
            raise RuntimeError("Unexpected PostgreSQL revocation result")
        return IAMRevocationReceipt(revocation_id, request_id, result)


class IAMRevocationSynchronizer:
    """At-least-once signed delivery with remote ACK only after SQL commit.

    If remote acknowledgement fails, callers retry. The SQL event receipt is
    idempotent; no false acknowledgement is emitted before SQL commits.
    """

    def __init__(
        self, *, source: TrustedIAMRevocationEventSource,
        acknowledger: SignedIAMRevocationAcknowledger,
    ) -> None:
        if not callable(getattr(source, "poll", None)) or not callable(
            getattr(source, "acknowledge", None)
        ):
            raise ValueError("Trusted revocation source contract required")
        self._source = source
        self._acknowledger = acknowledger

    def sync_once(self, *, limit: int = 32) -> tuple[IAMRevocationReceipt, ...]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Bounded revocation sync batch required")
        signed_events = self._source.poll(limit=limit)
        if not isinstance(signed_events, tuple) or len(signed_events) > limit:
            raise PrivilegedAccessDenied("Invalid trusted revocation batch")
        receipts = []
        for event in signed_events:
            receipt = self._acknowledger.apply(event)
            try:
                self._source.acknowledge(
                    revocation_id=receipt.revocation_id, status=receipt.status
                )
            except Exception as exc:
                raise IAMRevocationAckPending(
                    "PostgreSQL receipt committed, provider ACK pending; retry safely"
                ) from exc
            receipts.append(receipt)
        return tuple(receipts)
