"""L02-07h composition boundary for restricted privileged control-plane roles.

This factory verifies the two PostgreSQL login identities before composing the
application service. It is not a production process/network isolation boundary,
not an IAM implementation and not a secure secret distribution mechanism.
"""

import psycopg

from ...application.privileged_operations import (
    ApprovalVerificationPort,
    OperatorIdentityPort,
    PrivilegedPolicyPort,
    PrivilegedRoleService,
    TimePort,
)
from .delegated_control_plane import DelegatedPrivilegedControlPlane
from .delegated_privileged_audit import DelegatedPrivilegedAudit


class PrivilegedCompositionDenied(PermissionError):
    """A credential is not dedicated to the required SQL capability."""


def _require_restricted_login(dsn: str, expected: str) -> None:
    if not isinstance(dsn, str) or not dsn.strip():
        raise PrivilegedCompositionDenied("Dedicated SQL credential required")
    with psycopg.connect(dsn) as conn:
        identity = conn.execute(
            "SELECT session_user,rolsuper,rolcreaterole,rolbypassrls,"
            "rolcreatedb,rolreplication FROM pg_catalog.pg_roles "
            "WHERE rolname=session_user"
        ).fetchone()
        if identity != (expected, False, False, False, False, False):
            raise PrivilegedCompositionDenied("Unexpected or privileged SQL login")
        can_read_audit = conn.execute(
            "SELECT has_table_privilege(session_user, "
            "'company_configuration.privileged_operation_audit', 'SELECT')"
        ).fetchone()[0]
        if can_read_audit:
            raise PrivilegedCompositionDenied("Raw privileged audit access forbidden")
        function_grants = conn.execute(
            "SELECT "
            "has_function_privilege(session_user, "
            "'company_configuration.cp_append_privileged_audit("
            "uuid,uuid,text,text,text,text,text,text,text,text)', 'EXECUTE'), "
            "has_function_privilege(session_user, "
            "'company_configuration.cp_execute_fence("
            "uuid,text,text,text,text,text,text)', 'EXECUTE')"
        ).fetchone()
        required = (True, False) if expected == "cc_privileged_audit" else (False, True)
        if function_grants != required:
            raise PrivilegedCompositionDenied("SQL capability separation mismatch")


def build_restricted_privileged_service(
    *, audit_writer_dsn: str, control_plane_dsn: str,
    identity: OperatorIdentityPort, approvals: ApprovalVerificationPort,
    policy: PrivilegedPolicyPort, clock: TimePort,
) -> PrivilegedRoleService:
    """Fail closed if a schema owner, runtime or swapped capability DSN is given."""
    _require_restricted_login(audit_writer_dsn, "cc_privileged_audit")
    _require_restricted_login(control_plane_dsn, "cc_control_plane")
    return PrivilegedRoleService(
        identity=identity, approvals=approvals, policy=policy, clock=clock,
        audit=DelegatedPrivilegedAudit(audit_writer_dsn),
        fence=DelegatedPrivilegedControlPlane(control_plane_dsn),
    )
