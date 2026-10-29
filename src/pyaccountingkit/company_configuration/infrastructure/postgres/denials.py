"""Durable denied-decision sink for externally authenticated principals.

It records a minimal, pseudonymous-scoped security event independently of the
business UoW. The trusted authentication adapter owns unauthenticated failures.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import psycopg

from ...application.ports import TrustedPrincipal


class PostgresDenialAudit:
    def __init__(
        self, dsn: str, *, clock: Callable[[], datetime] | None = None
    ) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("A denial audit database DSN is required")
        self._dsn = dsn
        self._clock = clock or (lambda: datetime.now(UTC))

    def record_denial(
        self, *, principal: TrustedPrincipal, action: str,
        reason_code: str, correlation_id: str | None,
    ) -> None:
        if not isinstance(principal, TrustedPrincipal):
            raise TypeError("Unverified principal cannot enter durable decision audit")
        if reason_code not in ("TENANT_MISMATCH", "PERMISSION_DENIED"):
            raise ValueError("Unexpected denied-decision reason")
        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Denial audit requires a timezone-aware datetime")
        # The authenticated tenant is the authoritative storage partition.
        # Never use an untrusted requested scope as an RLS identity.
        with psycopg.connect(self._dsn) as conn:
            conn.execute("SELECT set_config('app.tenant_id', %s, true)", (principal.tenant_id,))
            conn.execute(
                "INSERT INTO company_configuration.authorization_denials "
                "(record_id, tenant_id, actor_id, action, reason_code, "
                "correlation_id, recorded_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    uuid4(), principal.tenant_id, principal.actor_id, action,
                    reason_code, correlation_id, now,
                ),
            )
