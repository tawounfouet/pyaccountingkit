"""Owner-only PostgreSQL incident decisions, without role DDL or outcome inference.

All resolution rows are immutable audit evidence. The owner DSN is a protected
control-plane capability; deployment must prohibit use by request handlers.
"""

from datetime import datetime
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from ...application.privileged_incidents import (
    IncidentDecisionConflict,
    IncidentDecisionReceipt,
    IncidentDecisionRequest,
    VerifiedIncidentApproval,
)
from ...application.privileged_operations import PrivilegedAccessDenied, VerifiedOperator


class PostgresPrivilegedIncidentRepository:
    """One transaction locks the review, validates eligibility, records decision."""

    def __init__(self, owner_dsn: str) -> None:
        if not isinstance(owner_dsn, str) or not owner_dsn.strip():
            raise ValueError("Explicit trusted owner DSN required")
        self._dsn = owner_dsn

    def record_denial(
        self, *, request: IncidentDecisionRequest, actor: VerifiedOperator,
        code: str, recorded_at: datetime,
    ) -> None:
        if code not in (
            "TENANT_MISMATCH", "PERMISSION_DENIED", "APPROVAL_INVALID", "SOD_VIOLATION",
        ):
            raise ValueError("Unrecognized denial reason")
        with psycopg.connect(self._dsn) as conn:
            conn.execute(
                "INSERT INTO company_configuration.privileged_incident_denials "
                "(denial_id,review_id,tenant_id,actor_id,reason_code,recorded_at) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (uuid4(), request.review_id, actor.tenant_id, actor.actor_id, code, recorded_at),
            )

    def record_decision(
        self, *, request: IncidentDecisionRequest, actor: VerifiedOperator,
        approval: VerifiedIncidentApproval, recorded_at: datetime,
    ) -> IncidentDecisionReceipt:
        decision_id = uuid4()
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            # Lock original review. A second reviewer cannot insert a duplicate
            # decision while the first is active; the UNIQUE key is final guard.
            row = conn.execute(
                "SELECT r.request_id,r.tenant_id,r.actor_id,r.reviewer_id, "
                "r.observed_outcome FROM company_configuration.privileged_reconciliation_reviews r "
                "WHERE r.review_id=%s FOR UPDATE OF r",
                (request.review_id,),
            ).fetchone()
            if row is None or row["tenant_id"] != request.tenant_id:
                raise IncidentDecisionConflict("Review is missing or outside authorized tenant")
            if row["observed_outcome"] != "UNKNOWN":
                raise IncidentDecisionConflict("Only UNKNOWN incidents can be decided")
            # Even a late outcome should prohibit treating the record as an
            # outstanding incident. A historical UNKNOWN is not overwritten.
            terminal = conn.execute(
                "SELECT 1 FROM company_configuration.privileged_operation_audit "
                "WHERE request_id=%s AND phase IN ('SUCCEEDED','FAILED','CANCELLED') "
                "LIMIT 1",
                (row["request_id"],),
            ).fetchone()
            if terminal is not None:
                raise IncidentDecisionConflict("A terminal operation record now exists")
            people = (row["actor_id"], row["reviewer_id"], actor.actor_id,
                      approval.approver_id)
            if any(not person for person in people) or len(set(people)) != 4:
                raise PrivilegedAccessDenied("Four distinct effective identities required")
            inserted = conn.execute(
                "INSERT INTO company_configuration.privileged_incident_decisions "
                "(decision_id,review_id,request_id,tenant_id,original_operator_id, "
                "original_reviewer_id,decision_actor_id,checker_id,approval_id, "
                "evidence_reference,justification,disposition,observed_outcome,recorded_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'UNKNOWN',%s) "
                "ON CONFLICT (review_id) DO NOTHING RETURNING decision_id",
                (decision_id, request.review_id, row["request_id"], request.tenant_id,
                 row["actor_id"], row["reviewer_id"], actor.actor_id,
                 approval.approver_id, approval.approval_id, request.evidence_reference,
                 request.justification, request.disposition, recorded_at),
            ).fetchone()
            if inserted is None:
                raise IncidentDecisionConflict("Review already has a recorded decision")
        return IncidentDecisionReceipt(
            decision_id, request.review_id, request.tenant_id,
            request.disposition, "UNKNOWN",
        )
