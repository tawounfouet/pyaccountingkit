"""G3-C02b3b2a: transaction-local actor grant epoch fence primitive.

This adapter never provisions grant state: an independently authorized,
separately deployed IAM projection owner must do so. A caller-created proof
is NOT identity attestation or proof of a real IAM grant.
"""

from dataclasses import dataclass
from re import fullmatch
from uuid import UUID

import psycopg

from .tenant_boundary import require_tenant_connection


@dataclass(frozen=True, slots=True)
class ActorGrantEpochReference:
    """Reference to owner-projected IAM grant state, NOT its cryptographic proof."""

    tenant_id: str
    grant_id: UUID
    grant_version: int
    actor_id: str
    action: str
    target_id: UUID
    authority_issuer: str
    decision_sha256: str

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, str) or not value or value != value.strip()
            for value in (
                self.tenant_id, self.actor_id, self.action, self.authority_issuer,
            )
        ):
            raise ValueError("Canonical scoped actor grant identity required")
        if (
            type(self.grant_id) is not UUID
            or type(self.target_id) is not UUID
            or type(self.grant_version) is not int
            or self.grant_version < 1
            or not isinstance(self.decision_sha256, str)
            or fullmatch(r"[a-f0-9]{64}", self.decision_sha256) is None
        ):
            raise ValueError("Grant epoch UUID/version and decision SHA256 required")


class PostgresActorGrantEpochFence:
    """Call INSIDE an independent SQL issuer's existing transaction.

    The PostgreSQL function keeps a SHARE lock until that SAME transaction
    commits, serializing owner revocation. Committing a separate connection
    does not protect any later business transaction.
    """

    def require(
        self, *, connection: psycopg.Connection, reference: ActorGrantEpochReference,
    ) -> None:
        if not isinstance(reference, ActorGrantEpochReference):
            raise TypeError("Verified owner-projection reference required")
        if not isinstance(connection, psycopg.Connection) or connection.autocommit:
            raise ValueError("A live, non-autocommit SQL issuer transaction is required")
        require_tenant_connection(connection, reference.tenant_id)
        connection.execute(
            "SELECT company_configuration.require_org_actor_grant_epoch("
            "%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                reference.tenant_id, reference.grant_id, reference.grant_version,
                reference.actor_id, reference.action, reference.target_id,
                reference.authority_issuer, reference.decision_sha256,
            ),
        )
