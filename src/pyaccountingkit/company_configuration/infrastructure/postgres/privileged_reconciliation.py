"""Durable, owner-only PostgreSQL identification of unresolved privileged intents.

No DDL is executed and an old INTENT is never classified SUCCEEDED or FAILED.
A caller must use the IAM-gated PrivilegedReconciliationService; raw owner DSN
is part of the separately protected operational control plane.
"""

from datetime import datetime
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from ...application.privileged_reconciliation import PrivilegedReview


class PostgresPrivilegedReviewRepository:
    def __init__(self, owner_dsn: str) -> None:
        if not isinstance(owner_dsn, str) or not owner_dsn.strip():
            raise ValueError("Explicit owner-only DSN required")
        self._dsn = owner_dsn

    def mark_stale(
        self, *, tenant_id: str, reviewer_id: str, cutoff: datetime,
        detected_at: datetime, limit: int,
    ) -> tuple[PrivilegedReview, ...]:
        if (not tenant_id or not reviewer_id or not isinstance(cutoff, datetime)
                or not isinstance(detected_at, datetime) or not 1 <= limit <= 100):
            raise ValueError("Valid scoped privileged review request required")
        result: list[PrivilegedReview] = []
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            # Row locks serialize competing reviewers, and the UNIQUE request_id
            # constraint is the last line of defense against duplicate evidence.
            candidates = conn.execute(
                "SELECT i.request_id, i.tenant_id, i.login_role, i.operation, "
                "i.actor_id, i.recorded_at "
                "FROM company_configuration.privileged_operation_audit AS i "
                "WHERE i.phase='INTENT' AND i.tenant_id=%s AND i.recorded_at<=%s "
                "AND NOT EXISTS (SELECT 1 FROM "
                "company_configuration.privileged_operation_audit AS o "
                "WHERE o.request_id=i.request_id "
                "AND o.phase IN ('SUCCEEDED','FAILED','CANCELLED')) "
                "AND NOT EXISTS (SELECT 1 FROM "
                "company_configuration.privileged_reconciliation_reviews AS r "
                "WHERE r.request_id=i.request_id) "
                "ORDER BY i.recorded_at, i.request_id FOR UPDATE OF i SKIP LOCKED "
                "LIMIT %s",
                (tenant_id, cutoff, limit),
            ).fetchall()
            for row in candidates:
                review_id = uuid4()
                inserted = conn.execute(
                    "INSERT INTO company_configuration.privileged_reconciliation_reviews "
                    "(review_id, request_id, tenant_id, login_role, operation, "
                    "actor_id, reviewer_id, intent_recorded_at, detected_at, "
                    "review_reason, observed_outcome) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'OUTCOME_MISSING','UNKNOWN') "
                    "ON CONFLICT (request_id) DO NOTHING RETURNING review_id",
                    (review_id, row['request_id'], row['tenant_id'], row['login_role'],
                     row['operation'], row['actor_id'], reviewer_id, row['recorded_at'],
                     detected_at),
                ).fetchone()
                if inserted:
                    result.append(PrivilegedReview(
                        review_id=review_id, request_id=row['request_id'],
                        tenant_id=row['tenant_id'], login_role=row['login_role'],
                        operation=row['operation'], detected_at=detected_at,
                        observed_outcome='UNKNOWN',
                    ))
        return tuple(result)
