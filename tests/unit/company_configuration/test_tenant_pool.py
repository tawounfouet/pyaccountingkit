"""Dependency-free pool boundary proofs with simulated physical connections."""

from contextlib import contextmanager
from dataclasses import replace

import pytest

from pyaccountingkit.company_configuration.infrastructure.postgres.tenant_pool import (
    PoolGenerationConflict,
    TenantCredential,
    TenantPoolDenied,
    TenantPoolRegistry,
)


class Secrets:
    def __init__(self):
        self.values = {}
        self.failed = False

    def get(self, *, tenant_id, role_kind):
        if self.failed:
            raise OSError("vault unavailable")
        return self.values[tenant_id, role_kind]


def credential(tenant, role="runtime", generation=1, dsn="postgres://redacted"):
    return TenantCredential(tenant, role, f"cc_{role}_{tenant[-1]}", generation, dsn)


class FakePool:
    def __init__(self, dsn):
        self.dsn = dsn
        self.closed = False
        self.checkouts = 0

    @contextmanager
    def connection(self):
        if self.closed:
            raise AssertionError("Retired pool reused")
        self.checkouts += 1
        yield {"dsn": self.dsn}

    def close(self):
        self.closed = True


def manager():
    secrets = Secrets()
    pools = []

    def build(dsn, max_size):
        assert max_size == 3
        pool = FakePool(dsn)
        pools.append(pool)
        return pool

    reg = TenantPoolRegistry(
        secrets, max_size=3, pool_factory=build,
        verifier=lambda conn, tenant, login: None,
    )
    return reg, secrets, pools


def test_physical_pools_are_separated_by_tenant_and_role():
    reg, secrets, pools = manager()
    secrets.values["tenant-a", "runtime"] = credential("tenant-a", dsn="dsn-a")
    secrets.values["tenant-b", "runtime"] = credential("tenant-b", dsn="dsn-b")
    secrets.values["tenant-a", "dispatcher"] = credential(
        "tenant-a", "dispatcher", dsn="dsn-dispatch"
    )
    with reg.connection(tenant_id="tenant-a", role_kind="runtime") as a:
        assert a["dsn"] == "dsn-a"
    with reg.connection(tenant_id="tenant-b", role_kind="runtime") as b:
        assert b["dsn"] == "dsn-b"
    with reg.connection(tenant_id="tenant-a", role_kind="dispatcher") as d:
        assert d["dsn"] == "dsn-dispatch"
    with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
        pass
    assert len(pools) == 3
    assert pools[0].checkouts == 2
    reg.close()
    assert all(p.closed for p in pools)


def test_rotation_retires_old_pool_without_reusing_connection():
    reg, secrets, pools = manager()
    secrets.values["tenant-a", "runtime"] = credential("tenant-a", dsn="old-secret")
    with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
        pass
    secrets.values["tenant-a", "runtime"] = credential(
        "tenant-a", generation=2, dsn="new-secret"
    )
    with reg.connection(tenant_id="tenant-a", role_kind="runtime") as conn:
        assert conn["dsn"] == "new-secret"
    assert len(pools) == 2 and pools[0].closed
    assert "new-secret" not in repr(reg)
    reg.close()


def test_inflight_connection_retained_until_context_exits():
    reg, secrets, pools = manager()
    secrets.values["tenant-a", "runtime"] = credential("tenant-a", dsn="old")
    with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
        secrets.values["tenant-a", "runtime"] = credential(
            "tenant-a", generation=2, dsn="new"
        )
        with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
            assert not pools[0].closed
        assert not pools[0].closed
    assert pools[0].closed
    reg.close()


def test_provider_outage_fails_closed_and_drops_idle_pool():
    reg, secrets, pools = manager()
    secrets.values["tenant-a", "runtime"] = credential("tenant-a")
    with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
        pass
    secrets.failed = True
    with pytest.raises(OSError, match="vault unavailable"):
        with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
            pytest.fail("Provider outage should never authorize cached pool")
    assert pools[0].closed
    reg.close()


def test_invalid_secret_scope_and_epoch_regression_fail_closed():
    reg, secrets, pools = manager()
    secrets.values["tenant-a", "runtime"] = credential("tenant-a", generation=3)
    with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
        pass
    secrets.values["tenant-a", "runtime"] = credential("tenant-a", generation=2)
    with pytest.raises(PoolGenerationConflict):
        with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
            pass
    assert pools[0].closed
    secrets.values["tenant-a", "runtime"] = credential("tenant-b")
    with pytest.raises(TenantPoolDenied):
        with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
            pass
    reg.close()


def test_same_generation_secret_change_is_rejected_and_secret_repr_redacted():
    reg, secrets, pools = manager()
    first = credential("tenant-a", dsn="postgres://user:very-private-password@host")
    assert "very-private-password" not in repr(first)
    secrets.values["tenant-a", "runtime"] = first
    with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
        pass
    secrets.values["tenant-a", "runtime"] = replace(first, dsn="different")
    with pytest.raises(PoolGenerationConflict):
        with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
            pass
    assert pools[0].closed
    reg.close()


def test_connection_identity_failure_is_never_returned_to_caller():
    reg, secrets, pools = manager()
    secrets.values["tenant-a", "runtime"] = credential("tenant-a")
    reg._verifier = lambda conn, tenant, login: (_ for _ in ()).throw(TenantPoolDenied("bad"))
    with pytest.raises(TenantPoolDenied):
        with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
            pytest.fail("No connection should be yielded")
    reg.close()


def test_invalid_secret_and_registry_closed():
    with pytest.raises(TenantPoolDenied):
        TenantCredential("tenant-a", "unexpected", "cc_runtime_a", 1, "x")
    with pytest.raises(TenantPoolDenied):
        TenantCredential("tenant-a", "runtime", "cc_dispatcher_a", 1, "x")
    reg, secrets, _ = manager()
    reg.close()
    with pytest.raises(TenantPoolDenied, match="closed"):
        with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
            pass


def test_epoch_highwater_survives_provider_outage_and_later_replay():
    reg, secrets, pools = manager()
    secrets.values["tenant-a", "runtime"] = credential("tenant-a", generation=5)
    with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
        pass
    secrets.failed = True
    with pytest.raises(OSError):
        with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
            pass
    secrets.failed = False
    secrets.values["tenant-a", "runtime"] = credential("tenant-a", generation=4)
    with pytest.raises(PoolGenerationConflict):
        with reg.connection(tenant_id="tenant-a", role_kind="runtime"):
            pass
    assert len(pools) == 1 and pools[0].closed
    reg.close()
