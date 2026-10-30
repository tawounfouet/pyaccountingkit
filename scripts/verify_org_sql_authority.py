"""G3-C01 read-only fail-closed L03 SQL authority deployment posture audit.

Checks a *specific* deployment role topology supplied explicitly by an operator.
It does not create roles, issue credentials, certify human IAM, or edit records.
Never pass DSNs on CLI; CC_PG_ADMIN_DSN is read from the environment.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from typing import Any

FAMILIES = ("company", "registry", "lifecycle", "membership")
FUNCTIONS: dict[str, tuple[str, ...]] = {
    "company": (
        "company_configuration.register_company_controlled("
        "text,uuid,text,text,text,text,text,integer,text,text,text,text,"
        "uuid,uuid,text,timestamptz)",
    ),
    "registry": (
        "company_configuration.register_establishment_controlled("
        "text,uuid,uuid,text,text,date,date,text,integer,text,text,text,text,"
        "uuid,uuid,text,timestamptz)",
        "company_configuration.register_legal_identifier_controlled("
        "text,uuid,uuid,text,text,text,text,date,date,text,text,text,text,text,"
        "uuid,uuid,text,timestamptz)",
    ),
    "lifecycle": (
        "company_configuration.transition_organization_controlled("
        "text,text,uuid,integer,text,text,timestamptz,text,text,text,text,text,"
        "uuid,uuid,text)",
    ),
    "membership": (
        "company_configuration.register_membership_revision_controlled("
        "text,uuid,integer,uuid,uuid,text,boolean,date,date,timestamptz,"
        "text,text,text,text,text,uuid,uuid,text)",
    ),
}
ISSUER_TABLES = {
    family: "company_configuration.organization_" + family + "_command_issuers"
    for family in FAMILIES
}

REGISTRATION_EVIDENCE = (
    "organization_command_requests",
    "organization_command_audit",
    "organization_command_outbox",
)
TABLES = (
    "organizational_companies",
    "organizational_establishments",
    "organizational_legal_identifiers",
    *REGISTRATION_EVIDENCE,
    "organizational_company_revisions",
    "organizational_establishment_revisions",
    "organization_lifecycle_requests",
    "organization_lifecycle_audit",
    "organization_lifecycle_outbox",
    "organizational_membership_revisions",
    "organization_membership_requests",
    "organization_membership_audit",
    "organization_membership_outbox",
)
# These tables are (historically) shared by Company and registry registration.
# Legacy runtime INSERT grants are tolerated ONLY if both target-kind INSERT
# guardians are installed and enabled. Other tables require zero runtime INSERT.
GUARDS = {
    "organizational_companies": (("org_company_issuer_guard", "guard_company_command_issuer"),),
    "organizational_establishments": (
        ("org_establishment_registry_issuer_guard", "guard_org_registry_issuer"),
    ),
    "organizational_legal_identifiers": (
        ("org_identifier_registry_issuer_guard", "guard_org_registry_issuer"),
    ),
    "organization_command_requests": (
        ("org_company_request_issuer_guard", "guard_company_command_issuer"),
        ("org_command_request_registry_issuer_guard", "guard_org_registry_issuer"),
    ),
    "organization_command_audit": (
        ("org_company_audit_issuer_guard", "guard_company_command_issuer"),
        ("org_command_audit_registry_issuer_guard", "guard_org_registry_issuer"),
    ),
    "organization_command_outbox": (
        ("org_company_outbox_issuer_guard", "guard_company_command_issuer"),
        ("org_command_outbox_registry_issuer_guard", "guard_org_registry_issuer"),
    ),
    "organizational_company_revisions": (
        ("company_revision_lifecycle_issuer", "guard_org_lifecycle_issuer"),
    ),
    "organizational_establishment_revisions": (
        ("establishment_revision_lifecycle_issuer", "guard_org_lifecycle_issuer"),
    ),
    "organization_lifecycle_requests": (
        ("lifecycle_request_issuer", "guard_org_lifecycle_issuer"),
    ),
    "organization_lifecycle_audit": (
        ("lifecycle_audit_issuer", "guard_org_lifecycle_issuer"),
    ),
    "organization_lifecycle_outbox": (
        ("lifecycle_outbox_issuer", "guard_org_lifecycle_issuer"),
    ),
    "organizational_membership_revisions": (
        ("org_membership_revision_issuer_guard", "guard_org_membership_issuer"),
    ),
    "organization_membership_requests": (
        ("org_membership_request_issuer_guard", "guard_org_membership_issuer"),
    ),
    "organization_membership_audit": (
        ("org_membership_audit_issuer_guard", "guard_org_membership_issuer"),
    ),
    "organization_membership_outbox": (
        ("org_membership_outbox_issuer_guard", "guard_org_membership_issuer"),
    ),
}
# G3-C02b3b1: deferrable row guards must run on COMMIT, not merely INSERT.
COMMIT_FENCES = {
    "organization_command_requests": "org_cmd_request_commit_issuer_fence",
    "organization_command_audit": "org_cmd_audit_commit_issuer_fence",
    "organization_command_outbox": "org_cmd_outbox_commit_issuer_fence",
    "organization_lifecycle_requests": "org_lifecycle_request_commit_issuer_fence",
    "organization_lifecycle_audit": "org_lifecycle_audit_commit_issuer_fence",
    "organization_lifecycle_outbox": "org_lifecycle_outbox_commit_issuer_fence",
    "organization_membership_requests": "org_membership_request_commit_issuer_fence",
    "organization_membership_audit": "org_membership_audit_commit_issuer_fence",
    "organization_membership_outbox": "org_membership_outbox_commit_issuer_fence",
}
SECURITY_FUNCTIONS = (
    "company_configuration.require_org_issuer_commit_fence(text,text)",
    "company_configuration.guard_org_issuer_commit_fence()",
    "company_configuration.guard_company_command_issuer()",
    "company_configuration.require_org_registry_issuer(text)",
    "company_configuration.guard_org_registry_issuer()",
    "company_configuration.require_org_lifecycle_issuer(text)",
    "company_configuration.guard_org_lifecycle_issuer()",
    "company_configuration.require_org_membership_issuer(text)",
    "company_configuration.guard_org_membership_issuer()",
)
AUTHORITY_SOURCES = (
    "company_configuration.require_org_issuer_commit_fence(text,text)",
    "company_configuration.guard_company_command_issuer()",
    "company_configuration.require_org_registry_issuer(text)",
    "company_configuration.require_org_lifecycle_issuer(text)",
    "company_configuration.require_org_membership_issuer(text)",
)

@dataclass(frozen=True)
class Claim:
    role: str
    tenant: str
    family: str = "runtime"


def parse_claims(runtime: list[str], issuer: list[str]) -> tuple[Claim, ...]:
    """Require a complete 4-family-per-tenant topology, not a partial subset."""
    claims: list[Claim] = []
    for item in runtime:
        parts = item.split(":")
        if len(parts) != 2:
            raise ValueError("Runtime role must be ROLE:TENANT")
        claims.append(Claim(parts[0], parts[1]))
    for item in issuer:
        parts = item.split(":")
        if len(parts) != 3 or parts[0] not in FAMILIES:
            raise ValueError("Issuer must be FAMILY:ROLE:TENANT")
        claims.append(Claim(parts[1], parts[2], parts[0]))
    if not runtime:
        raise ValueError("At least one runtime login must be checked")
    for item in claims:
        if not item.role or not item.tenant or any(
            part.strip() != part for part in (item.role, item.tenant)
        ):
            raise ValueError("Role and tenant names must be nonblank and canonical")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\-]{0,62}", item.role):
            raise ValueError("Role login has an invalid character or length")
        if ":" in item.tenant or "\x00" in item.tenant:
            raise ValueError("Tenant identity must not contain separators")
    if len({c.role for c in claims}) != len(claims):
        raise ValueError("Runtime and issuer SQL login identities must be distinct")
    tenants = {c.tenant for c in claims if c.family == "runtime"}
    for tenant in tenants:
        for family in FAMILIES:
            matching = [c for c in claims if c.tenant == tenant and c.family == family]
            if len(matching) != 1:
                raise ValueError(f"{tenant}: exactly one {family} issuer is required")
    if any(c.tenant not in tenants for c in claims):
        raise ValueError("Every issuer must have a corresponding runtime tenant")
    if len(claims) != len(tenants) * (len(FAMILIES) + 1):
        raise ValueError("Exactly one runtime and each issuer family per tenant")
    return tuple(claims)


def _one(conn: Any, statement: str, *values: Any) -> Any:
    row = conn.execute(statement, values).fetchone()
    return row[0] if row else None


def audit(conn: Any, claims: tuple[Claim, ...]) -> list[str]:
    """Inspect live roles/ACL/RLS/guards; return all violations, never mutate.

    DB lookup failure is intentionally fatal to the caller, not a PASS.
    The connection must be an independent read-only-capable DBA/auditor that
    can inspect pg_catalog and owner-managed issuer/binding tables.
    """
    failures: list[str] = []
    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    # Refuse overly narrow direct calls as well as malformed CLI input.
    parse_claims(
        [f"{c.role}:{c.tenant}" for c in claims if c.family == "runtime"],
        [f"{c.family}:{c.role}:{c.tenant}" for c in claims if c.family != "runtime"],
    )

    functions = tuple(fn for group in FUNCTIONS.values() for fn in group)
    for func in (*functions, *SECURITY_FUNCTIONS):
        result = conn.execute(
            "SELECT prosecdef,proconfig,pg_catalog.pg_get_functiondef(oid),"
            "EXISTS(SELECT 1 FROM pg_catalog.aclexplode("
            "COALESCE(proacl,pg_catalog.acldefault('f',proowner))) acl "
            "WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE') "
            "FROM pg_catalog.pg_proc WHERE oid=%s::regprocedure",
            (func,),
        ).fetchone()
        check(result is not None, f"missing SQL function: {func}")
        if result is None:
            continue
        secure, settings, definition, public_execute = result
        check(bool(secure), f"not SECURITY DEFINER: {func}")
        check(
            any(s.replace(" ", "") == "search_path=pg_catalog,pg_temp"
                for s in (settings or [])),
            f"unpinned search_path: {func}",
        )
        check(not public_execute, f"PUBLIC EXECUTE exposed: {func}")
        if func in AUTHORITY_SOURCES:
            check(
                "session_user" in definition and "bound_tenant()" in definition,
                f"original login/tenant SQL check missing: {func}",
            )

    for table in TABLES:
        result = conn.execute(
            "SELECT c.relrowsecurity,c.relforcerowsecurity "
            "FROM pg_catalog.pg_class c "
            "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='company_configuration' AND c.relname=%s",
            (table,),
        ).fetchone()
        check(result == (True, True), f"RLS/FORCE RLS missing: {table}")
        for trigger, expected_proc in GUARDS[table]:
            found = conn.execute(
                "SELECT t.tgenabled,t.tgtype,p.proname "
                "FROM pg_catalog.pg_trigger t "
                "JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid "
                "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
                "JOIN pg_catalog.pg_proc p ON p.oid=t.tgfoid "
                "WHERE n.nspname='company_configuration' AND c.relname=%s "
                "AND t.tgname=%s AND NOT t.tgisinternal",
                (table, trigger),
            ).fetchone()
            check(
                found is not None and found[0] in ("O", "A")
                and found[1] & 7 == 7 and found[2] == expected_proc,
                f"required enabled BEFORE INSERT ROW guard missing: {table}.{trigger}",
            )

    for table, trigger in COMMIT_FENCES.items():
        found = conn.execute(
            "SELECT t.tgenabled,t.tgtype,t.tgdeferrable,t.tginitdeferred,p.proname "
            "FROM pg_catalog.pg_trigger t "
            "JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid "
            "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
            "JOIN pg_catalog.pg_proc p ON p.oid=t.tgfoid "
            "WHERE n.nspname='company_configuration' AND c.relname=%s "
            "AND t.tgname=%s AND NOT t.tgisinternal",
            (table, trigger),
        ).fetchone()
        check(
            found is not None and found[0] in ("O", "A")
            and found[1] & 7 == 5 and found[2] is True
            and found[3] is True
            and found[4] == "guard_org_issuer_commit_fence",
            f"required DEFERRABLE INITIALLY DEFERRED issuer COMMIT guard missing: "
            f"{table}.{trigger}",
        )

    for claim in claims:
        role, tenant, family = claim.role, claim.tenant, claim.family
        flags = conn.execute(
            "SELECT rolcanlogin,rolsuper,rolcreaterole,rolcreatedb,"
            "rolbypassrls,rolinherit FROM pg_catalog.pg_roles WHERE rolname=%s",
            (role,),
        ).fetchone()
        check(
            flags == (True, False, False, False, False, False),
            f"role is absent or not a non-inheriting, login-only, unprivileged role: {role}",
        )
        bound = _one(
            conn, "SELECT tenant_id FROM company_configuration.tenant_role_bindings "
            "WHERE login_role=%s", role,
        )
        check(bound == tenant, f"bound_tenant role/tenant mismatch: {role}")
        if family != "runtime":
            issuer_record = conn.execute(
                "SELECT tenant_id,enabled FROM " + ISSUER_TABLES[family]
                + " WHERE login_role=%s", (role,),
            ).fetchone()
            check(issuer_record == (tenant, True), f"{family} issuer disabled/misbound: {role}")
        for table in TABLES:
            full = "company_configuration." + table
            # Registration evidence is shared between two separately guarded
            # registration target kinds, retaining some legacy runtime grants.
            if family != "runtime" or table not in REGISTRATION_EVIDENCE:
                has_insert = _one(
                    conn, "SELECT has_table_privilege(%s,%s,'INSERT')", role, full,
                )
                check(has_insert is False, f"direct table INSERT: {role} -> {table}")
                # Column grants can also authorize an INSERT even if table
                # has_table_privilege returns false.
                col = _one(
                    conn, "SELECT a.attname FROM pg_catalog.pg_attribute a "
                    "WHERE a.attrelid=%s::regclass AND a.attnum>0 "
                    "AND NOT a.attisdropped "
                    "AND has_column_privilege(%s,%s,a.attname,'INSERT') "
                    "LIMIT 1", full, role, full,
                )
                check(col is None, f"column-level INSERT: {role} -> {table}.{col}")
            for permission in ("UPDATE", "DELETE", "TRUNCATE"):
                permitted = _one(
                    conn, "SELECT has_table_privilege(%s,%s,%s)",
                    role, full, permission,
                )
                check(permitted is False, f"{permission} table grant: {role} -> {table}")
        # All emitter allowlists and tenant role bindings must be owner-only.
        for managed in ("company_configuration.tenant_role_bindings", *ISSUER_TABLES.values()):
            for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
                check(
                    _one(conn, "SELECT has_table_privilege(%s,%s,%s)",
                         role, managed, privilege) is False,
                    f"owner-managed authority ACL breached: {role} -> {managed}/{privilege}",
                )
        for target_family, funcs in FUNCTIONS.items():
            for func in funcs:
                execute = _one(
                    conn, "SELECT has_function_privilege(%s,%s,'EXECUTE')",
                    role, func,
                )
                expected = family == target_family
                check(
                    execute is expected,
                    f"EXECUTE {'missing' if expected else 'exposed'}: {role} -> {func}",
                )
    issuers = [c for c in claims if c.family != "runtime"]
    for runtime in (c for c in claims if c.family == "runtime"):
        for issuer in issuers:
            check(
                _one(conn, "SELECT pg_has_role(%s,%s,'SET')",
                     runtime.role, issuer.role) is False,
                f"runtime may SET ROLE into issuer: {runtime.role} -> {issuer.role}",
            )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", action="append", required=True, metavar="ROLE:TENANT")
    parser.add_argument(
        "--issuer", action="append", required=True, metavar="FAMILY:ROLE:TENANT",
    )
    args = parser.parse_args(argv)
    try:
        claims = parse_claims(args.runtime, args.issuer)
        # Do not interpolate or print the DSN; preferably use an external
        # read-only auditor with SELECT on owner-managed policy tables.
        import psycopg

        dsn = os.environ["CC_PG_ADMIN_DSN"]
        with psycopg.connect(dsn, autocommit=True) as conn:
            failures = audit(conn, claims)
    except (ValueError, KeyError, ImportError) as exc:
        print(f"FAIL G3-C01 invalid configuration: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        # Don't print arbitrary database error details: they may contain
        # connection parameters. A failed DB read is always NOT QUALIFIED.
        print(
            f"FAIL G3-C01 unable to verify SQL authority ({type(exc).__name__})",
            file=sys.stderr,
        )
        return 2
    if failures:
        for finding in failures:
            print("FAIL G3-C01 " + finding)
        print(f"NOT QUALIFIED: {len(failures)} SQL authority violations")
        return 1
    print(
        f"PASS G3-C01: {len(claims)} isolated SQL logins, "
        f"{len(TABLES)} FORCE RLS tables, all issuer grants/guards verified; "
        "database posture only (NOT human IAM qualification)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
