"""G3-C02b1 durable signed-command nonce adapter for isolated gateway workers.

No SQL issuer/ordinary API credentials are stored or retrieved here. Each
consumption uses an explicitly supplied, separately provisioned nonce SQL
principal, and commits before the command's DDD transaction starts.
"""

from datetime import datetime
from uuid import UUID

import psycopg

from .tenant_boundary import require_tenant_connection


class PostgresDurableCommandNonceStore:
    """Atomic, cross-connection one-time token consumption; fail closed on outage.

    Caller must provide a nonce-only SQL principal. This adapter cannot provide
    secret-manager isolation or assert that a human is independently authenticated.
    """

    def __init__(self, dsn: str) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("Dedicated nonce-consumer PostgreSQL DSN required")
        self._dsn = dsn

    def __repr__(self) -> str:
        return "PostgresDurableCommandNonceStore(dsn=<redacted>)"

    def consume(
        self, *, tenant_id: str, issuer: str, nonce: UUID, expires_at: datetime,
    ) -> bool:
        if (
            not isinstance(tenant_id, str) or not tenant_id
            or tenant_id != tenant_id.strip()
            or not isinstance(issuer, str) or not issuer or issuer != issuer.strip()
            or type(nonce) is not UUID
            or type(expires_at) is not datetime or expires_at.utcoffset() is None
        ):
            raise ValueError("Canonical signed nonce, tenant, issuer and expiry required")
        with psycopg.connect(self._dsn) as conn:
            require_tenant_connection(conn, tenant_id)
            result = conn.execute(
                "SELECT company_configuration.consume_organization_command_nonce("
                "%s,%s,%s,%s)",
                (tenant_id, issuer, nonce, expires_at),
            ).fetchone()
            if result is None or type(result[0]) is not bool:
                raise RuntimeError("Unverified database nonce consumption outcome")
            # Connection context manager commits before returning. The nonce is
            # permanently burned even if later SQL business logic rolls back.
            return result[0]
