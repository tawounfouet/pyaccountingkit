"""PostgreSQL-local durable revocation acknowledgement for a restricted SQL login.

No remote IAM connection or credential is embedded in this adapter.
"""

import psycopg

from ..iam.revocation import VerifiedIamRevocation


class PostgresIamRevocationRepository:
    """An independent SQL capability; requires the cc_iam_revocation login.

    The owner-installed SQL function provides per-request advisory locking,
    fence row locking, immutable tombstones and replay-safe receipts.
    """

    def __init__(self, dsn: str) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("Dedicated revocation capability DSN required")
        self._dsn = dsn

    def __repr__(self) -> str:
        return "PostgresIamRevocationRepository(dsn=<redacted>)"

    def apply(self, evidence: VerifiedIamRevocation) -> str:
        if not isinstance(evidence, VerifiedIamRevocation):
            raise TypeError("Verified revocation evidence required")
        with psycopg.connect(self._dsn) as conn:
            result = conn.execute(
                "SELECT company_configuration.cp_ack_iam_revocation("
                "%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    evidence.event_id, evidence.request_id, evidence.tenant_id,
                    evidence.login_role, evidence.operation, evidence.issuer,
                    evidence.signer_kid, evidence.revoker_id, evidence.signed_digest,
                ),
            ).fetchone()
            if result is None:
                raise RuntimeError("No SQL revocation receipt")
            return result[0]
