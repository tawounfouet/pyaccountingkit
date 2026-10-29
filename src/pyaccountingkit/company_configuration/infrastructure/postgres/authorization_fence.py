"""Owner-only PostgreSQL-local authorization fence for privileged SQL role DDL.

The fence/revocation serialization applies ONLY to a PostgreSQL-backed grant.
Remote IAM changes require explicit, acknowledged propagation to this database.
No web/runtime service should receive the database owner DSN.
"""
from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg
from psycopg import sql

from ...application.authorization_fence import PrivilegedFencePermit
from .role_lifecycle import (
    PostgresTenantRoleOperator,
    RoleLifecycleDenied,
    RoleLifecycleReceipt,
)


class PrivilegedFenceDenied(PermissionError):
    """No matching active, unexpired database-side fence."""


@dataclass(frozen=True, slots=True)
class FencedRoleOperation:
    request_id: UUID
    tenant_id: str
    login_role: str
    operation: str
    actor_id: str
    approval_id: str


class PostgresPrivilegedAuthorizationFence:
    """Issue, revoke and consume a fence under separate owner-only SQL credentials.

    Consumption, role DDL and evidence commit atomically in PostgreSQL.
    Backend drain occurs after commit and can still fail. The historical
    privileged-operation outcome journal remains a separate transaction.
    """

    def __init__(self, owner_dsn: str) -> None:
        if not isinstance(owner_dsn, str) or not owner_dsn.strip():
            raise ValueError("Explicit protected control-plane owner DSN required")
        self._dsn = owner_dsn
        self._roles = PostgresTenantRoleOperator(owner_dsn)

    @staticmethod
    def _event(
        conn: psycopg.Connection, request_id: UUID, tenant_id: str,
        actor_id: str, action: str,
    ) -> None:
        conn.execute(
            "INSERT INTO company_configuration.privileged_fence_events "
            "(event_id,request_id,tenant_id,actor_id,action) "
            "VALUES (%s,%s,%s,%s,%s)",
            (uuid4(), request_id, tenant_id, actor_id, action),
        )

    def issue(self, permit: PrivilegedFencePermit) -> None:
        """Only trusted control-plane issuance may call this owner-side method."""
        if not isinstance(permit, PrivilegedFencePermit):
            raise TypeError("Validated permit snapshot required")
        with psycopg.connect(self._dsn) as conn:
            now = conn.execute("SELECT clock_timestamp()").fetchone()[0]
            if permit.expires_at <= now:
                raise PrivilegedFenceDenied("Approval already expired")
            conn.execute(
                "INSERT INTO company_configuration.privileged_authorization_fences "
                "(request_id,tenant_id,login_role,operation,actor_id,approver_id,"
                "approval_id,expires_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    permit.request_id, permit.tenant_id, permit.login_role,
                    permit.operation, permit.actor_id, permit.approver_id,
                    permit.approval_id, permit.expires_at,
                ),
            )
            self._event(
                conn, permit.request_id, permit.tenant_id, permit.actor_id, "ISSUED"
            )

    def revoke(self, *, request_id: UUID, tenant_id: str, revoked_by: str) -> bool:
        """Serialize SQL-side revocation with DDL; False if already terminal.

        An external IAM revocation NOT propagated here does not block execution.
        """
        if not isinstance(request_id, UUID) or not tenant_id or not revoked_by:
            raise PrivilegedFenceDenied("Canonical scoped revocation required")
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(
                "SELECT state FROM company_configuration.privileged_authorization_fences "
                "WHERE request_id=%s AND tenant_id=%s FOR UPDATE",
                (request_id, tenant_id),
            ).fetchone()
            if row is None:
                raise PrivilegedFenceDenied("Scoped authorization fence not found")
            if row[0] != "ACTIVE":
                return False
            conn.execute(
                "UPDATE company_configuration.privileged_authorization_fences "
                "SET state='REVOKED', revoked_at=clock_timestamp() "
                "WHERE request_id=%s", (request_id,),
            )
            self._event(conn, request_id, tenant_id, revoked_by, "REVOKED")
        return True

    def execute(
        self, operation: FencedRoleOperation, *, new_password: str | None = None
    ) -> RoleLifecycleReceipt:
        """Lock fence until role DDL and durable consumption commit together."""
        if not isinstance(operation, FencedRoleOperation):
            raise TypeError("FencedRoleOperation required")
        if operation.operation not in ("rotate", "revoke"):
            raise PrivilegedFenceDenied("Unsupported operation")
        if operation.operation == "rotate":
            if (
                not isinstance(new_password, str) or len(new_password) < 16
                or "\x00" in new_password
            ):
                raise RoleLifecycleDenied("Credential does not meet input requirements")
        elif new_password is not None:
            raise RoleLifecycleDenied("Revoke operation cannot carry a password")

        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(
                "SELECT tenant_id,login_role,operation,actor_id,approval_id,state,expires_at "
                "FROM company_configuration.privileged_authorization_fences "
                "WHERE request_id=%s FOR UPDATE", (operation.request_id,),
            ).fetchone()
            if (
                row is None or row[:5] != (
                    operation.tenant_id, operation.login_role, operation.operation,
                    operation.actor_id, operation.approval_id,
                ) or row[5] != "ACTIVE"
            ):
                raise PrivilegedFenceDenied("Matching active authorization fence required")
            if row[6] <= conn.execute("SELECT clock_timestamp()").fetchone()[0]:
                raise PrivilegedFenceDenied("Authorization fence expired")
            self._roles._validate_target(operation.login_role, operation.tenant_id)
            self._roles._assert_binding(conn, operation.login_role, operation.tenant_id)
            if operation.operation == "rotate":
                conn.execute(
                    sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                        sql.Identifier(operation.login_role), sql.Literal(new_password)
                    )
                )
            else:
                conn.execute(
                    sql.SQL("ALTER ROLE {} NOLOGIN").format(
                        sql.Identifier(operation.login_role)
                    )
                )
                conn.execute(
                    "DELETE FROM company_configuration.tenant_role_bindings "
                    "WHERE login_role=%s::name AND tenant_id=%s",
                    (operation.login_role, operation.tenant_id),
                )
            conn.execute(
                "UPDATE company_configuration.privileged_authorization_fences "
                "SET state='CONSUMED',consumed_at=clock_timestamp() "
                "WHERE request_id=%s", (operation.request_id,),
            )
            self._event(
                conn, operation.request_id, operation.tenant_id,
                operation.actor_id, "CONSUMED",
            )
        # Outside transaction: a failed drain never permits replay of consumed DDL.
        terminated = self._roles._drain(operation.login_role)
        return RoleLifecycleReceipt(
            operation.login_role, operation.tenant_id, operation.operation, terminated
        )
