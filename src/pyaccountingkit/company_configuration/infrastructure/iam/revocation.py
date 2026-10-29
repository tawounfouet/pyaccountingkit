"""Signed IAM revocation receipt pipeline with explicit remote acknowledgement.

The evidence source and SQL credential MUST be controlled independently of
ordinary tenant-facing requests. No live IAM provider is bundled here.
"""

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ...application.privileged_operations import PrivilegedAccessDenied
from .signed_evidence import PinnedSignedEvidenceVerifier


@dataclass(frozen=True, slots=True)
class VerifiedIamRevocation:
    event_id: UUID
    request_id: UUID
    tenant_id: str
    login_role: str
    operation: str
    issuer: str
    signer_kid: str
    revoker_id: str
    signed_digest: str


@dataclass(frozen=True, slots=True)
class IamRevocationReceipt:
    event_id: UUID
    request_id: UUID
    tenant_id: str
    disposition: str


class TrustedIamRevocationSource(Protocol):
    """Independent source and ACK client; NEVER a caller-supplied JWS echo."""

    def read(self, event_id: UUID) -> str: ...

    def acknowledge(self, receipt: IamRevocationReceipt) -> None: ...


class IamRevocationRepositoryPort(Protocol):
    """Atomically persist the tombstone and apply SQL-local revocation."""

    def apply(self, evidence: VerifiedIamRevocation) -> str: ...


class RemoteAcknowledgementIncomplete(RuntimeError):
    """The local SQL receipt was committed, but remote acknowledgement failed."""

    def __init__(self, receipt: IamRevocationReceipt) -> None:
        super().__init__("IAM revocation persisted locally; remote ACK incomplete")
        self.receipt = receipt


class SignedIamRevocationProcessor:
    """Independently sourced, signed revocation with durable SQL-first ACK.

    TOMBSTONED means issuance is blocked even before a fence exists.
    REVOKED means an ACTIVE fence was revoked in the SQL transaction.
    ALREADY_CONSUMED is an incident signal, not successful prevention.
    """

    _OUTCOMES = frozenset({
        "TOMBSTONED", "REVOKED", "ALREADY_REVOKED", "ALREADY_CONSUMED",
    })

    def __init__(
        self, *, verifier: PinnedSignedEvidenceVerifier,
        source: TrustedIamRevocationSource,
        repository: IamRevocationRepositoryPort,
    ) -> None:
        if verifier._trust.kind != "revocation":
            raise ValueError("Independent revocation signing root required")
        if not callable(getattr(source, "read", None)) or not callable(
            getattr(source, "acknowledge", None)
        ):
            raise ValueError("Independent IAM source and acknowledgement required")
        if not callable(getattr(repository, "apply", None)):
            raise ValueError("Durable revocation repository required")
        self._verifier = verifier
        self._source = source
        self._repository = repository

    def ingest(self, event_id: UUID) -> IamRevocationReceipt:
        """Persist signed revocation; SQL trigger enqueues ACK atomically."""
        if not isinstance(event_id, UUID):
            raise PrivilegedAccessDenied("Canonical UUID event reference required")
        try:
            token = self._source.read(event_id)
        except Exception as exc:
            raise PrivilegedAccessDenied("Trusted IAM revocation source unavailable") from exc
        claims = self._verifier.verify(token)
        try:
            event_ref = UUID(claims["jti"])
            request_ref = UUID(claims["request_id"])
            operation = claims["operation"]
            if event_ref != event_id or operation not in ("rotate", "revoke"):
                raise ValueError("Incorrect event ID or operation")
            login_role = claims["login_role"]
            if not isinstance(login_role, str) or not login_role.startswith(
                ("cc_runtime_", "cc_dispatcher_", "cc_inbox_")
            ):
                raise ValueError("Unapproved SQL login target")
            header_bytes = token.split(".")[0]
            header = json.loads(
                base64.urlsafe_b64decode(header_bytes + "=" * (-len(header_bytes) % 4))
            )
            evidence = VerifiedIamRevocation(
                event_id=event_ref,
                request_id=request_ref,
                tenant_id=claims["tenant_id"],
                login_role=login_role,
                operation=operation,
                issuer=claims["iss"],
                signer_kid=header["kid"],
                revoker_id=claims["sub"],
                signed_digest=hashlib.sha256(token.encode("ascii")).hexdigest(),
            )
        except (KeyError, ValueError, TypeError, UnicodeError) as exc:
            raise PrivilegedAccessDenied("Revocation evidence scope invalid") from exc
        # If persistence fails, the upstream provider MUST NOT receive an ACK.
        disposition = self._repository.apply(evidence)
        if disposition not in self._OUTCOMES:
            raise RuntimeError("Unknown SQL revocation disposition, no remote ACK")
        return IamRevocationReceipt(
            event_id, request_ref, evidence.tenant_id, disposition
        )

    def process(self, event_id: UUID) -> IamRevocationReceipt:
        """Legacy immediate-ACK compatibility; use ingest() + outbox in L02-07k."""
        receipt = self.ingest(event_id)
        try:
            self._source.acknowledge(receipt)
        except Exception as exc:
            raise RemoteAcknowledgementIncomplete(receipt) from exc
        return receipt
