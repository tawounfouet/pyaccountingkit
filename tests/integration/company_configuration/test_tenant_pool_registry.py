"""PostgreSQL L02-07: per-tenant physical pools and credential epochs."""

import os

import pytest

psycopg = pytest.importorskip("psycopg")
pytest.importorskip("psycopg_pool")

from pyaccountingkit.company_configuration.infrastructure.postgres.tenant_boundary import (  # noqa: E402
    TenantConnectionMismatch,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.tenant_pool import (  # noqa: E402
    PoolGenerationConflict,
    TenantCredential,
    TenantPoolDenied,
    TenantPoolRegistry,
)

APP_A = os.getenv("CC_PG_DSN")
APP_B = os.getenv("CC_PG_DSN_B")
DISPATCH_A = os.getenv("CC_PG_DISPATCH_DSN")
pytestmark = pytest.mark.skipif(
    not (APP_A and APP_B and DISPATCH_A),
    reason="Tenant pooling tests need PostgreSQL tenant roles and DSNs",
)


class Secrets:
    def __init__(self):
        self.values = {
            ("tenant-a", "runtime"): TenantCredential(
                "tenant-a", "runtime", "cc_runtime_a", 1, APP_A or "unset"
            ),
            ("tenant-b", "runtime"): TenantCredential(
                "tenant-b", "runtime", "cc_runtime_b", 1, APP_B or "unset"
            ),
            ("tenant-a", "dispatcher"): TenantCredential(
                "tenant-a", "dispatcher", "cc_dispatcher_a", 1, DISPATCH_A or "unset"
            ),
        }
        self.available = True

    def get(self, *, tenant_id, role_kind):
        if not self.available:
            raise ConnectionError("vault unavailable")
        return self.values[tenant_id, role_kind]


def test_real_connections_keep_tenant_identity_separated_across_pools():
    provider = Secrets()
    with TenantPoolRegistry(provider, max_size=2) as pools:
        with pools.connection(tenant_id="tenant-a", role_kind="runtime") as conn:
            assert conn.execute("SELECT session_user").fetchone()[0] == "cc_runtime_a"
            assert (
                conn.execute("SELECT company_configuration.bound_tenant()").fetchone()[0]
                == "tenant-a"
            )
        with pools.connection(tenant_id="tenant-b", role_kind="runtime") as conn:
            assert conn.execute("SELECT session_user").fetchone()[0] == "cc_runtime_b"
            assert (
                conn.execute("SELECT company_configuration.bound_tenant()").fetchone()[0]
                == "tenant-b"
            )
        with pools.connection(tenant_id="tenant-a", role_kind="dispatcher") as conn:
            assert conn.execute("SELECT session_user").fetchone()[0] == "cc_dispatcher_a"
        assert len(pools._entries) == 3
        assert len({id(e.pool) for e in pools._entries.values()}) == 3


def test_forged_secret_with_correct_tenant_but_wrong_role_is_rejected():
    provider = Secrets()
    provider.values["tenant-a", "runtime"] = TenantCredential(
        "tenant-a", "runtime", "cc_runtime_a", 1, APP_B
    )
    with TenantPoolRegistry(provider, max_size=1) as pools:
        with pytest.raises((TenantPoolDenied, TenantConnectionMismatch)):
            with pools.connection(tenant_id="tenant-a", role_kind="runtime"):
                pytest.fail("wrong tenant login should not escape")


def test_wrong_role_kind_credentials_are_not_reused_across_pools():
    provider = Secrets()
    provider.values["tenant-a", "runtime"] = TenantCredential(
        "tenant-a", "runtime", "cc_runtime_a", 1, DISPATCH_A
    )
    with TenantPoolRegistry(provider, max_size=1) as pools:
        with pytest.raises(TenantPoolDenied, match="login"):
            with pools.connection(tenant_id="tenant-a", role_kind="runtime"):
                pytest.fail("dispatcher login should not become runtime")


def test_epoch_change_retires_pool_and_provisioning_outage_is_fail_closed():
    provider = Secrets()
    with TenantPoolRegistry(provider, max_size=1) as pools:
        with pools.connection(tenant_id="tenant-a", role_kind="runtime"):
            pass
        first = pools._entries["tenant-a", "runtime"].pool
        provider.values["tenant-a", "runtime"] = TenantCredential(
            "tenant-a", "runtime", "cc_runtime_a", 2, APP_A
        )
        with pools.connection(tenant_id="tenant-a", role_kind="runtime"):
            pass
        assert first.closed
        second = pools._entries["tenant-a", "runtime"].pool
        assert second is not first
        provider.available = False
        with pytest.raises(ConnectionError, match="vault unavailable"):
            with pools.connection(tenant_id="tenant-a", role_kind="runtime"):
                pytest.fail("stale cached pool should be forbidden")
        assert second.closed


def test_same_epoch_changed_secret_fails_closed():
    provider = Secrets()
    with TenantPoolRegistry(provider, max_size=1) as pools:
        with pools.connection(tenant_id="tenant-a", role_kind="runtime"):
            pass
        provider.values["tenant-a", "runtime"] = TenantCredential(
            "tenant-a", "runtime", "cc_runtime_a", 1, APP_B
        )
        with pytest.raises(PoolGenerationConflict):
            with pools.connection(tenant_id="tenant-a", role_kind="runtime"):
                pass
