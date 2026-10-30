"""G3-C02b1 PostgreSQL 16 durable nonce: multi-session uniqueness and denial.

Only ephemeral test SQL users; no deployed IAM/secret custody is claimed.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from pyaccountingkit.company_configuration.infrastructure.postgres.organization_nonce import (  # noqa: E402
    PostgresDurableCommandNonceStore,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.tenant_boundary import (  # noqa: E402
    TenantConnectionMismatch,
)

ADMIN = os.getenv("CC_PG_ADMIN_DSN")
RUNTIME = os.getenv("CC_PG_DSN")
COMPANY_WRITER = os.getenv("CC_PG_ORG_COMPANY_WRITER_DSN")
NONCE_A = os.getenv("CC_PG_ORG_NONCE_CONSUMER_DSN")
NONCE_B = os.getenv("CC_PG_ORG_NONCE_CONSUMER_DSN_B")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, RUNTIME, COMPANY_WRITER, NONCE_A, NONCE_B)),
    reason="G3-C02b1 needs independently bound ephemeral PostgreSQL nonce users",
)

FUNCTION = (
    "company_configuration.consume_organization_command_nonce("
    "text,text,uuid,timestamptz)"
)


@pytest.fixture(autouse=True)
def isolated_nonces():
    if not ADMIN:
        yield
        return
    with psycopg.connect(ADMIN) as conn:
        conn.execute("TRUNCATE company_configuration.organization_command_nonces")
    yield
    with psycopg.connect(ADMIN) as conn:
        conn.execute("TRUNCATE company_configuration.organization_command_nonces")


def count_rows() -> int:
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            "SELECT count(*) FROM company_configuration.organization_command_nonces"
        ).fetchone()[0]


def expiry():
    return datetime.now(UTC) + timedelta(minutes=2)


def test_nonce_survives_connection_close_and_new_adapter_instances():
    nonce = uuid4()
    first = PostgresDurableCommandNonceStore(NONCE_A)
    assert first.consume(
        tenant_id="tenant-a", issuer="trusted-iam", nonce=nonce, expires_at=expiry(),
    )
    # A second process/connection reconstructs the adapter without local state.
    second = PostgresDurableCommandNonceStore(NONCE_A)
    assert not second.consume(
        tenant_id="tenant-a", issuer="trusted-iam", nonce=nonce, expires_at=expiry(),
    )
    assert count_rows() == 1


def test_concurrent_same_signed_nonce_has_exactly_one_winner():
    gate = Barrier(3)
    nonce = uuid4()

    def attempt(_index):
        gate.wait(timeout=20)
        return PostgresDurableCommandNonceStore(NONCE_A).consume(
            tenant_id="tenant-a", issuer="trusted-iam",
            nonce=nonce, expires_at=expiry(),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(attempt, 0)
        b = pool.submit(attempt, 1)
        gate.wait(timeout=20)
        assert sorted([a.result(timeout=20), b.result(timeout=20)]) == [False, True]
    assert count_rows() == 1


def test_global_jti_unique_even_across_tenant_sessions():
    nonce = uuid4()
    assert PostgresDurableCommandNonceStore(NONCE_A).consume(
        tenant_id="tenant-a", issuer="trusted-iam", nonce=nonce, expires_at=expiry(),
    )
    assert not PostgresDurableCommandNonceStore(NONCE_B).consume(
        tenant_id="tenant-b", issuer="trusted-iam", nonce=nonce, expires_at=expiry(),
    )
    assert count_rows() == 1


def test_other_issuer_can_use_distinct_namespace_with_same_jti():
    nonce = uuid4()
    store = PostgresDurableCommandNonceStore(NONCE_A)
    assert store.consume(
        tenant_id="tenant-a", issuer="trusted-iam", nonce=nonce, expires_at=expiry(),
    )
    assert store.consume(
        tenant_id="tenant-a", issuer="other-pinned-iam",
        nonce=nonce, expires_at=expiry(),
    )
    assert count_rows() == 2


def test_nonce_rollback_does_not_create_row():
    nonce = uuid4()
    with pytest.raises(RuntimeError, match="simulated crash"):
        with psycopg.connect(NONCE_A) as conn:
            assert conn.execute(
                "SELECT company_configuration.consume_organization_command_nonce("
                "%s,%s,%s,%s)",
                ("tenant-a", "trusted-iam", nonce, expiry()),
            ).fetchone()[0]
            raise RuntimeError("simulated crash")
    assert count_rows() == 0


def test_expired_or_far_future_proposal_rejected_by_database_clock():
    store = PostgresDurableCommandNonceStore(NONCE_A)
    for until in (
        datetime.now(UTC) - timedelta(minutes=1),
        datetime.now(UTC) + timedelta(days=1),
    ):
        with pytest.raises(psycopg.errors.CheckViolation):
            store.consume(
                tenant_id="tenant-a", issuer="trusted-iam",
                nonce=uuid4(), expires_at=until,
            )
    assert count_rows() == 0


def test_wrong_tenant_and_untrusted_runtime_fail_with_no_persistence():
    store = PostgresDurableCommandNonceStore(NONCE_A)
    with pytest.raises(TenantConnectionMismatch):
        store.consume(
            tenant_id="tenant-b", issuer="trusted-iam",
            nonce=uuid4(), expires_at=expiry(),
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME) as conn:
            conn.execute(
                "SELECT company_configuration.consume_organization_command_nonce("
                "%s,%s,%s,%s)",
                ("tenant-a", "trusted-iam", uuid4(), expiry()),
            )
    assert count_rows() == 0


def test_direct_dml_and_role_escalation_denied_by_sql_permissions():
    for dsn in (RUNTIME, COMPANY_WRITER, NONCE_A):
        with psycopg.connect(dsn) as conn:
            assert conn.execute(
                "SELECT has_table_privilege(current_user,"
                "'company_configuration.organization_command_nonces','INSERT')"
            ).fetchone()[0] is False
            assert conn.execute(
                "SELECT has_table_privilege(current_user,"
                "'company_configuration.organization_nonce_consumers','UPDATE')"
            ).fetchone()[0] is False
            assert conn.execute(
                "SELECT has_function_privilege(current_user,%s,'EXECUTE')",
                (FUNCTION,),
            ).fetchone()[0] is (dsn == NONCE_A)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(RUNTIME) as conn:
            conn.execute("SET ROLE cc_org_nonce_consumer_a")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(NONCE_A) as conn:
            conn.execute(
                "INSERT INTO company_configuration.organization_command_nonces "
                "(tenant_id,issuer,nonce,expires_at) VALUES (%s,%s,%s,%s)",
                ("tenant-a", "trusted-iam", uuid4(), expiry()),
            )
    assert count_rows() == 0


def test_owner_revocation_is_fail_closed_and_restores_without_writes():
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "UPDATE company_configuration.organization_nonce_consumers "
            "SET enabled=false WHERE login_role='cc_org_nonce_consumer_a'"
        )
    try:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            PostgresDurableCommandNonceStore(NONCE_A).consume(
                tenant_id="tenant-a", issuer="trusted-iam",
                nonce=uuid4(), expires_at=expiry(),
            )
    finally:
        with psycopg.connect(ADMIN) as conn:
            conn.execute(
                "UPDATE company_configuration.organization_nonce_consumers "
                "SET enabled=true WHERE login_role='cc_org_nonce_consumer_a'"
            )
    assert count_rows() == 0


def test_unavailable_store_fails_without_accidental_positive_result():
    with pytest.raises(psycopg.OperationalError):
        PostgresDurableCommandNonceStore(
            "postgresql://127.0.0.1:1/nonexistent?connect_timeout=1"
        ).consume(
            tenant_id="tenant-a", issuer="trusted-iam",
            nonce=uuid4(), expires_at=expiry(),
        )
    assert count_rows() == 0
