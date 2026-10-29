"""L02-04 Inbox qualification on PostgreSQL 16, not a C10 consumer certificate."""

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Barrier, Thread

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg.rows import dict_row  # noqa: E402
from test_postgres_uow import build_service, create  # noqa: E402

from pyaccountingkit.company_configuration.infrastructure.postgres.dispatch import (  # noqa: E402
    OutboxEnvelope,
    PostgresOutboxDispatcher,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.inbox import (  # noqa: E402
    CountingProjectionHandler,
    InboxPayloadConflict,
    InboxTenantMismatch,
    PostgresInboxConsumer,
    UnsupportedInboxSchema,
)

ADMIN_DSN = os.getenv("CC_PG_ADMIN_DSN")
INBOX_DSN = os.getenv("CC_PG_INBOX_DSN")
INBOX_DSN_B = os.getenv("CC_PG_INBOX_DSN_B")
DISPATCH_DSN = os.getenv("CC_PG_DISPATCH_DSN")
pytestmark = pytest.mark.skipif(
    not (ADMIN_DSN and INBOX_DSN and DISPATCH_DSN),
    reason="Inbox integration requires dedicated PostgreSQL admin/inbox/dispatcher DSNs",
)


@pytest.fixture(autouse=True)
def reset_test_data():
    if not (ADMIN_DSN and INBOX_DSN and DISPATCH_DSN):
        yield
        return
    # Disposal-only CI schema owner; never truncate accounting evidence in production.
    with psycopg.connect(ADMIN_DSN) as conn:
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


def source_event(*, tenant="tenant-a"):
    scope, actor, _, service = build_service(tenant=tenant)
    receipt = service.create(create(scope), principal=actor)
    with psycopg.connect(ADMIN_DSN, row_factory=dict_row) as conn:
        row = conn.execute(
            "SELECT event_id, tenant_id, company_id, entity_id, event_type, "
            "schema_version, revision, correlation_id, recorded_at "
            "FROM company_configuration.outbox_events WHERE event_id=%s",
            (receipt.event_id,),
        ).fetchone()
    return scope, OutboxEnvelope(**dict(row))


def inbox(
    *, tenant="tenant-a", consumer="demo-read-model", producer="company-config", handler=None
):
    return PostgresInboxConsumer(
        INBOX_DSN_B if tenant == "tenant-b" else INBOX_DSN,
        tenant_id=tenant,
        consumer_id=consumer,
        producer_id=producer,
        handler=handler or CountingProjectionHandler(),
    )


def counts():
    with psycopg.connect(ADMIN_DSN) as conn:
        return (
            conn.execute("SELECT count(*) FROM company_configuration.inbox_receipts").fetchone()[0],
            conn.execute(
                "SELECT coalesce(sum(applied_count), 0) "
                "FROM company_configuration.inbox_projection_counts"
            ).fetchone()[0],
        )


class Clock:
    def __init__(self):
        self.value = datetime.now(UTC) + timedelta(days=1)

    def now(self):
        return self.value

    def advance(self, seconds):
        self.value += timedelta(seconds=seconds)


def test_migrations_are_checksum_verified_after_inbox_update():
    from pyaccountingkit.company_configuration.infrastructure.postgres.migrate import (
        apply_migrations,
    )

    assert apply_migrations(ADMIN_DSN) == []


def test_process_and_replay_are_atomic_and_deduplicated():
    scope, event = source_event()
    consumer = inbox(tenant=scope.tenant_id)
    assert consumer.process(event).applied
    assert consumer.process(event).duplicate
    assert counts() == (1, 1)
    # Evidence and projection are distinct from producer accounting state.
    with psycopg.connect(ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.legal_entities"
        ).fetchone()[0] == 1


def test_outbox_crash_after_inbox_commit_replays_without_double_effect():
    scope, event = source_event()
    consumer = inbox(tenant=scope.tenant_id)
    clock = Clock()
    worker = PostgresOutboxDispatcher(
        DISPATCH_DSN, tenant_id=scope.tenant_id, worker_id="worker-one",
        publisher=consumer, clock=clock.now, lease_seconds=4,
    )

    def lost_ack(claim, *, failure):
        if failure is None:
            raise OSError("simulated crash after inbox commit before outbox ack")
        raise AssertionError("unexpected delivery failure")

    worker._complete = lost_ack
    with pytest.raises(OSError, match="simulated crash"):
        worker.dispatch_once()
    assert counts() == (1, 1)
    clock.advance(10)
    restarted = PostgresOutboxDispatcher(
        DISPATCH_DSN, tenant_id=scope.tenant_id, worker_id="worker-two",
        publisher=consumer, clock=clock.now, lease_seconds=4,
    )
    assert restarted.dispatch_once().delivered == 1
    assert counts() == (1, 1)
    with psycopg.connect(ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.outbox_delivery "
            "WHERE delivered_at IS NOT NULL"
        ).fetchone()[0] == 1
    assert str(event.event_id)


def test_failed_handler_rolls_back_receipt_and_partial_projection():
    scope, event = source_event()

    class FailingHandler:
        def apply(self, connection, event, *, consumer_id):
            CountingProjectionHandler().apply(connection, event, consumer_id=consumer_id)
            raise OSError("simulated projection failure")

    broken = inbox(tenant=scope.tenant_id, handler=FailingHandler())
    with pytest.raises(OSError, match="projection failure"):
        broken.process(event)
    assert counts() == (0, 0)
    assert inbox(tenant=scope.tenant_id).process(event).applied
    assert counts() == (1, 1)


def test_same_producer_event_id_changed_content_rejected():
    _, event = source_event()
    consumer = inbox()
    assert consumer.process(event).applied
    with pytest.raises(InboxPayloadConflict):
        consumer.process(replace(event, event_type="legal_entity.malicious_replay"))
    assert counts() == (1, 1)


def test_unknown_schema_fails_before_receipt():
    _, event = source_event()
    with pytest.raises(UnsupportedInboxSchema):
        inbox().process(replace(event, schema_version=2))
    assert counts() == (0, 0)


def test_tenant_mismatch_rejected_before_db_access():
    _, event = source_event(tenant="tenant-b")
    with pytest.raises(InboxTenantMismatch):
        inbox(tenant="tenant-a").process(event)
    assert counts() == (0, 0)


def test_dedup_key_includes_producer_and_consumer():
    _, event = source_event()
    assert inbox(producer="source-a", consumer="consumer-1").process(event).applied
    assert inbox(producer="source-b", consumer="consumer-1").process(event).applied
    assert inbox(producer="source-a", consumer="consumer-2").process(event).applied
    assert counts() == (3, 3)


def test_parallel_duplicate_delivery_has_one_sql_side_effect():
    _, event = source_event()
    barrier = Barrier(3)
    results = []
    errors = []
    consumer = inbox()

    def worker():
        barrier.wait()
        try:
            results.append(consumer.process(event).applied)
        except Exception as exc:
            errors.append(exc)

    threads = [Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    barrier.wait()
    for t in threads:
        t.join(timeout=10)
    assert not errors
    assert sorted(results) == [False, True]
    assert counts() == (1, 1)


def test_inbox_role_cannot_mutate_receipts_or_read_producer_evidence():
    _, event = source_event()
    inbox().process(event)
    with psycopg.connect(INBOX_DSN) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT count(*) FROM company_configuration.audit_records")
    with psycopg.connect(INBOX_DSN) as conn:
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (event.tenant_id,))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "UPDATE company_configuration.inbox_receipts "
                "SET event_type='tampered'"
            )


def test_rls_login_binding_cannot_be_spoofed_with_custom_guc():
    # A tenant-A login cannot read a tenant-B Inbox even after setting a malicious GUC.
    _, event = source_event(tenant="tenant-b")
    inbox(tenant="tenant-b").process(event)
    with psycopg.connect(INBOX_DSN) as conn:
        # Client GUCs are now ignored by RLS in favor of the bound session_user.
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", ("tenant-b",))
        visible = conn.execute(
            "SELECT count(*) FROM company_configuration.inbox_receipts"
        ).fetchone()[0]
        assert visible == 0  # session_user binds this login to tenant-a
