"""L02-05 adversarial tenant-bound login and RLS tests on real PostgreSQL."""

import os
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
from test_postgres_uow import build_service, create  # noqa: E402

from pyaccountingkit.company_configuration.application.service import (  # noqa: E402
    LegalEntityService,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.adapter import (  # noqa: E402
    PostgresUnitOfWork,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.dispatch import (  # noqa: E402
    PostgresOutboxDispatcher,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.inbox import (  # noqa: E402
    CountingProjectionHandler,
    PostgresInboxConsumer,
)
from pyaccountingkit.company_configuration.infrastructure.postgres import (  # noqa: E402
    tenant_boundary,
)

TenantConnectionMismatch = tenant_boundary.TenantConnectionMismatch

def bound_tenant(connection):
    return connection.execute("SELECT company_configuration.bound_tenant()").fetchone()[0]


def count_entities(connection):
    return connection.execute(
        "SELECT count(*) FROM company_configuration.legal_entities"
    ).fetchone()[0]


ADMIN = os.getenv("CC_PG_ADMIN_DSN")
A = os.getenv("CC_PG_DSN")
B = os.getenv("CC_PG_DSN_B")
UNBOUND = os.getenv("CC_PG_UNBOUND_DSN")
DISPATCH_A = os.getenv("CC_PG_DISPATCH_DSN")
INBOX_A = os.getenv("CC_PG_INBOX_DSN")
pytestmark = pytest.mark.skipif(
    not all((ADMIN, A, B, UNBOUND, DISPATCH_A, INBOX_A)),
    reason="Tenant-role DB proof requires dedicated test role credentials",
)


@pytest.fixture(autouse=True)
def reset_data():
    if not ADMIN:
        yield
        return
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            "TRUNCATE company_configuration.inbox_receipts, "
            "company_configuration.inbox_projection_counts, "
            "company_configuration.authorization_denials, "
            "company_configuration.outbox_delivery, "
            "company_configuration.legal_entities, "
            "company_configuration.idempotency_requests, "
            "company_configuration.audit_records, "
            "company_configuration.outbox_events CASCADE"
        )
    yield


def test_session_user_mapping_enforces_tenant_despite_malicious_guc():
    scope_a, actor_a, _, service_a = build_service(tenant="tenant-a")
    scope_b, actor_b, _, service_b = build_service(tenant="tenant-b")
    service_a.create(create(scope_a), principal=actor_a)
    service_b.create(create(scope_b), principal=actor_b)
    with psycopg.connect(A) as conn:
        assert conn.execute("SELECT session_user").fetchone()[0] == "cc_runtime_a"
        assert bound_tenant(conn) == "tenant-a"
        assert count_entities(conn) == 1
        conn.execute("SELECT set_config('app.tenant_id', 'tenant-b', true)")
        assert count_entities(conn) == 1
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.legal_entities WHERE tenant_id='tenant-b'"
        ).fetchone()[0] == 0
    with psycopg.connect(B) as conn:
        assert bound_tenant(conn) == "tenant-b"
        assert count_entities(conn) == 1


def test_cross_tenant_insert_is_denied_even_with_guc_spoof():
    with psycopg.connect(A) as conn:
        conn.execute("SELECT set_config('app.tenant_id', 'tenant-b', true)")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "INSERT INTO company_configuration.legal_entities "
                "(tenant_id, company_id, entity_id, legal_name, jurisdiction, "
                "functional_currency, revision) VALUES "
                "('tenant-b', %s, %s, 'Injection', 'FR', 'EUR', 1)",
                (uuid4(), uuid4()),
            )


def test_unregistered_login_cannot_access_tenant_rows():
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    with psycopg.connect(UNBOUND) as conn:
        assert bound_tenant(conn) is None
        conn.execute("SELECT set_config('app.tenant_id', 'tenant-a', true)")
        assert count_entities(conn) == 0


def test_runtime_login_cannot_change_role_or_provision_other_tenants():
    with psycopg.connect(A) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SET ROLE cc_runtime_b")
    with psycopg.connect(A) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SET SESSION AUTHORIZATION cc_runtime_b")
    with psycopg.connect(A) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM company_configuration.tenant_role_bindings")
    with psycopg.connect(A) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "UPDATE company_configuration.tenant_role_bindings SET tenant_id='tenant-b'"
            )


def test_search_path_and_transaction_reuse_cannot_change_bound_identity():
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    with psycopg.connect(A) as conn:
        conn.execute("SET search_path TO pg_temp, public")
        conn.execute("SELECT set_config('app.tenant_id', 'tenant-b', true)")
        assert bound_tenant(conn) == "tenant-a"
        assert count_entities(conn) == 1
        conn.commit()
        conn.execute("SELECT set_config('app.tenant_id', 'tenant-b', true)")
        assert bound_tenant(conn) == "tenant-a"
        assert count_entities(conn) == 1


def test_uow_rejects_incorrect_tenant_role_before_mutation():
    scope, actor, auth, _ = build_service(tenant="tenant-a")
    service = LegalEntityService(lambda: PostgresUnitOfWork(B), auth)
    with pytest.raises(TenantConnectionMismatch):
        service.create(create(scope), principal=actor)
    with psycopg.connect(ADMIN) as conn:
        assert count_entities(conn) == 0


def test_inbox_rejects_foreign_database_role():
    from test_inbox_consumer import source_event  # noqa: E402

    _, event = source_event(tenant="tenant-b")
    consumer = PostgresInboxConsumer(
        INBOX_A, tenant_id="tenant-b", consumer_id="count", producer_id="source",
        handler=CountingProjectionHandler(),
    )
    with pytest.raises(TenantConnectionMismatch):
        consumer.process(event)
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.inbox_receipts"
        ).fetchone()[0] == 0


def test_dispatcher_rejects_foreign_database_role():
    from test_inbox_consumer import source_event  # noqa: E402

    _, event = source_event(tenant="tenant-b")

    class NeverPublish:
        def publish(self, event):
            raise AssertionError("should not publish")

    dispatcher = PostgresOutboxDispatcher(
        DISPATCH_A, tenant_id="tenant-b", worker_id="misbound", publisher=NeverPublish()
    )
    with pytest.raises(TenantConnectionMismatch):
        dispatcher.dispatch_once()
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.outbox_delivery"
        ).fetchone()[0] == 0
    assert event.tenant_id == "tenant-b"


def test_untrusted_login_has_no_grant_on_immutable_audit_evidence():
    with psycopg.connect(INBOX_A) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT count(*) FROM company_configuration.audit_records")
