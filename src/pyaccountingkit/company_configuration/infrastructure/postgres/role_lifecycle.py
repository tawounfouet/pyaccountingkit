"""Owner-only operational candidate for PostgreSQL tenant login rotation/revocation.

This code is not exposed to application services or tenant users. An isolated,
privileged deployment operator must provide admin credentials. Credential custody,
server-side statement logging and external client pool draining remain open ADRs.
"""

import re
from dataclasses import dataclass

import psycopg
from psycopg import sql

from .tenant_boundary import TenantConnectionMismatch, require_tenant_connection


class RoleLifecycleDenied(PermissionError):
    """Requested operation does not match a registered, unprivileged tenant login."""


class SessionTerminationIncomplete(RuntimeError):
    """A role mutation committed, but one or more active sessions may still exist."""


@dataclass(frozen=True, slots=True)
class RoleLifecycleReceipt:
    """Non-secret administrative outcome. Do not include DSNs or passwords."""

    login_role: str
    tenant_id: str
    operation: str
    sessions_terminated: int


class PostgresTenantRoleOperator:
    """Minimal owner-authorized rotation and emergency revocation primitive.

    A rotation invalidates old passwords for new sessions and attempts to
    terminate *all* existing sessions of the login, including those of pools.
    A revocation atomically sets NOLOGIN and removes the tenant binding, then
    terminates existing backends. A failure to terminate is surfaced, never
    returned as a successful operation. This is NOT an identity management API.
    """

    _SAFE_ROLE = re.compile(r"cc_(?:runtime|dispatcher|inbox)_[a-z][a-z0-9_]*\Z")

    def __init__(self, admin_dsn: str) -> None:
        if not isinstance(admin_dsn, str) or not admin_dsn.strip():
            raise ValueError("An explicit administrator DSN is required")
        self._dsn = admin_dsn

    @classmethod
    def _validate_target(cls, login_role: str, expected_tenant: str) -> None:
        if not isinstance(login_role, str) or not cls._SAFE_ROLE.fullmatch(login_role):
            raise RoleLifecycleDenied("Not a permitted tenant login role")
        if (
            not isinstance(expected_tenant, str)
            or not expected_tenant.strip()
            or expected_tenant.strip() != expected_tenant
        ):
            raise RoleLifecycleDenied("Expected tenant is required")

    @staticmethod
    def _assert_binding(conn: psycopg.Connection, login_role: str, tenant: str) -> None:
        bound = conn.execute(
            "SELECT tenant_id FROM company_configuration.tenant_role_bindings "
            "WHERE login_role = %s::name FOR UPDATE",
            (login_role,),
        ).fetchone()
        if bound is None or bound[0] != tenant:
            raise RoleLifecycleDenied("Tenant login binding does not match request")
        role = conn.execute(
            "SELECT rolcanlogin, rolsuper, rolcreaterole, rolbypassrls "
            "FROM pg_catalog.pg_roles WHERE rolname = %s",
            (login_role,),
        ).fetchone()
        if role is None or not role[0] or any(role[1:]):
            raise RoleLifecycleDenied("Target must be a nonprivileged LOGIN role")

    def _drain(self, login_role: str) -> int:
        """Terminate all observable sessions; a partial result raises an alert.

        The admin role must be allowed to signal the target backends. A failed
        drain is an operational incident: never claim rotation/revocation complete.
        """
        with psycopg.connect(self._dsn, autocommit=True) as conn:
            results = conn.execute(
                "SELECT pg_catalog.pg_terminate_backend(pid, 5000) "
                "FROM pg_catalog.pg_stat_activity "
                "WHERE usename = %s AND pid <> pg_catalog.pg_backend_pid()",
                (login_role,),
            ).fetchall()
            if not all(value[0] for value in results):
                raise SessionTerminationIncomplete("Some tenant login sessions remain active")
            remaining = conn.execute(
                "SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE usename = %s",
                (login_role,),
            ).fetchone()[0]
            if remaining:
                raise SessionTerminationIncomplete("Tenant sessions still present after drain")
            return len(results)

    def rotate_password(
        self, *, login_role: str, expected_tenant: str, new_password: str
    ) -> RoleLifecycleReceipt:
        self._validate_target(login_role, expected_tenant)
        if not isinstance(new_password, str) or len(new_password) < 16 or "\x00" in new_password:
            raise RoleLifecycleDenied("New credential must meet minimum input requirements")
        with psycopg.connect(self._dsn) as conn:
            self._assert_binding(conn, login_role, expected_tenant)
            # PostgreSQL ALTER ROLE PASSWORD is a utility command; SQL Identifier
            # and Literal quote untrusted input safely. The password exists in
            # the SQL statement: production statement logging needs review.
            conn.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(login_role), sql.Literal(new_password)
                )
            )
        terminated = self._drain(login_role)
        return RoleLifecycleReceipt(login_role, expected_tenant, "rotate", terminated)

    def revoke_login(
        self, *, login_role: str, expected_tenant: str
    ) -> RoleLifecycleReceipt:
        self._validate_target(login_role, expected_tenant)
        with psycopg.connect(self._dsn) as conn:
            self._assert_binding(conn, login_role, expected_tenant)
            conn.execute(
                sql.SQL("ALTER ROLE {} NOLOGIN").format(sql.Identifier(login_role))
            )
            conn.execute(
                "DELETE FROM company_configuration.tenant_role_bindings "
                "WHERE login_role = %s::name AND tenant_id = %s",
                (login_role, expected_tenant),
            )
        terminated = self._drain(login_role)
        return RoleLifecycleReceipt(login_role, expected_tenant, "revoke", terminated)


class TenantConnectionFactory:
    """One-login, one-tenant checked connection factory; NOT a connection pool.

    Each checkout opens a fresh DB login and verifies the owner-managed binding.
    A pool integration must use a physically separate pool per tenant/role and
    discard all existing sessions when secrets change or access is revoked.
    """

    def __init__(self, dsn: str, *, tenant_id: str) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("Database DSN is required")
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ValueError("Tenant id is required")
        self._dsn = dsn
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"TenantConnectionFactory(tenant_id={self._tenant_id!r}, dsn=<redacted>)"

    def connect(self) -> psycopg.Connection:
        connection = psycopg.connect(self._dsn)
        try:
            require_tenant_connection(connection, self._tenant_id)
        except BaseException:
            connection.close()
            raise
        return connection
