"""PostgreSQL tenant security boundary derived from the authenticated login role.

The schema owner, provisioning automation and credential vault are trusted.
The application tenant claim, SET ROLE, search_path and app.* GUCs are not.
"""

import psycopg


class TenantConnectionMismatch(PermissionError):
    """The authenticated database login is not bound to the requested tenant."""


def require_tenant_connection(connection: psycopg.Connection, tenant_id: str) -> None:
    """Fail closed before accessing a tenant-scoped table.

    SQL RLS is the separate authoritative control for direct SQL queries. This
    preflight only improves early failure and error diagnosis for trusted adapters.
    """
    if not isinstance(tenant_id, str) or not tenant_id or tenant_id.strip() != tenant_id:
        raise TenantConnectionMismatch("A canonical tenant is required")
    row = connection.execute(
        "SELECT company_configuration.bound_tenant() AS bound_tenant"
    ).fetchone()
    bound = row["bound_tenant"] if isinstance(row, dict) else row[0] if row else None
    if bound != tenant_id:
        # Do not disclose the login role or other tenant identity to callers.
        raise TenantConnectionMismatch("Database connection is not bound to requested tenant")
