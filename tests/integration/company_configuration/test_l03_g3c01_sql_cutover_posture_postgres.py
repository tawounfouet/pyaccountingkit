"""G3-C01 SQL authority topology checks against actual PostgreSQL 16 roles.

No production IAM claim; owner/auditor reads only, negative tests roll back.
"""

import os

import pytest

psycopg = pytest.importorskip("psycopg")

from scripts.verify_org_sql_authority import audit, parse_claims  # noqa: E402

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
pytestmark = pytest.mark.skipif(
    not ADMIN, reason="G3-C01 needs independently scoped ephemeral SQL fixture",
)

CLAIMS = parse_claims(
    ["cc_runtime_a:tenant-a", "cc_runtime_b:tenant-b"],
    [
        f"{family}:cc_org_{family}_writer_{suffix}:{tenant}"
        for family in ("company", "registry", "lifecycle", "membership")
        for suffix, tenant in (("a", "tenant-a"), ("b", "tenant-b"))
    ],
)


def test_complete_role_topology_is_live_and_denies_all_direct_writes():
    with psycopg.connect(ADMIN) as conn:
        assert audit(conn, CLAIMS) == []


def test_revoked_issuer_binding_is_a_fatal_cutover_violation():
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE company_configuration.organization_membership_command_issuers "
            "SET enabled=false WHERE login_role='cc_org_membership_writer_a'"
        )
        try:
            findings = audit(conn, CLAIMS)
            assert any(
                "membership issuer disabled/misbound: cc_org_membership_writer_a" in x
                for x in findings
            )
        finally:
            conn.rollback()


def test_disabled_registration_evidence_guard_fails_posture_audit():
    """One disabled shared evidence guard must invalidate the cutover gate."""
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "ALTER TABLE company_configuration.organization_command_requests "
            "DISABLE TRIGGER org_command_request_registry_issuer_guard"
        )
        try:
            findings = audit(conn, CLAIMS)
            assert any(
                "required enabled BEFORE INSERT ROW guard missing: "
                "organization_command_requests.org_command_request_registry_issuer_guard"
                in x for x in findings
            )
        finally:
            conn.rollback()


def test_wrong_tenant_binding_fails_without_sql_mutation():
    """A self-declared tenant assignment does not override SQL role binding."""
    swapped = parse_claims(
        ["cc_runtime_a:tenant-a", "cc_runtime_b:tenant-b"],
        [
            f"{family}:cc_org_{family}_writer_{suffix}:{tenant}"
            for family in ("company", "registry", "lifecycle", "membership")
            for suffix, tenant in (
                (("b" if family == "company" else "a"), "tenant-a"),
                (("a" if family == "company" else "b"), "tenant-b"),
            )
        ],
    )
    with psycopg.connect(ADMIN) as conn:
        findings = audit(conn, swapped)
    assert any("bound_tenant role/tenant mismatch: cc_org_company_writer" in x
               for x in findings)
