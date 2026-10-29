"""FND-C05: crash/fencing/isolation proofs on real PostgreSQL 16.

These tests exercise the actual L02 outbox/inbox adapters; not an external
broker, upstream event signature, or C10 consumer contract certificate.
"""

import os
from datetime import UTC, datetime, timedelta

import pytest

psycopg = pytest.importorskip("psycopg")
from test_postgres_uow import build_service, create  # noqa: E402

from pyaccountingkit.company_configuration.infrastructure.postgres.dispatch import (  # noqa: E402
    DeliveryLeaseLost,
    PostgresOutboxDispatcher,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.inbox import (  # noqa: E402
    CountingProjectionHandler,
    PostgresInboxConsumer,
)

ADMIN_DSN = os.getenv("CC_PG_ADMIN_DSN")
DISPATCH_DSN = os.getenv("CC_PG_DISPATCH_DSN")
INBOX_DSN = os.getenv("CC_PG_INBOX_DSN")
pytestmark = pytest.mark.skipif(
    not all((ADMIN_DSN, DISPATCH_DSN, INBOX_DSN)),
    reason="FND-C05 requires trusted isolated PostgreSQL CI role credentials",
)


class Clock:
    def __init__(self):
        # Keep the test clock above any database-generated available_at.
        self.value = datetime.now(UTC) + timedelta(days=1)

    def now(self):
        return self.value

    def advance(self, seconds):
        self.value += timedelta(seconds=seconds)


class Publisher:
    def __init__(self, *, clock=None, delay=0):
        self.events = []
        self.clock = clock
        self.delay = delay

    def publish(self, event):
        self.events.append(event)
        if self.clock and self.delay:
            self.clock.advance(self.delay)


@pytest.fixture(autouse=True)
def clean_fnd_c05_tables():
    if not all((ADMIN_DSN, DISPATCH_DSN, INBOX_DSN)):
        yield
        return
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


def _event():
    scope, actor, _, service = build_service()
    return service.create(create(scope), principal=actor)


def _worker(publisher, clock, *, worker_id, attempts=3):
    return PostgresOutboxDispatcher(
        DISPATCH_DSN, tenant_id="tenant-a", worker_id=worker_id,
        publisher=publisher, clock=clock.now, lease_seconds=4,
        max_attempts=attempts, retry_seconds=2,
    )


def _delivery():
    with psycopg.connect(ADMIN_DSN) as conn:
        return conn.execute(
            "SELECT attempts,lease_owner,lease_token,lease_until,"
            "delivered_at,dead_letter_at,last_error "
            "FROM company_configuration.outbox_delivery"
        ).fetchone()


def _count(table):
    with psycopg.connect(ADMIN_DSN) as conn:
        return conn.execute(
            "SELECT count(*) FROM company_configuration." + table
        ).fetchone()[0]


def test_expired_lease_cannot_ack_even_before_reclaim_by_another_worker():
    event = _event()
    clock = Clock()
    slow = Publisher(clock=clock, delay=5)
    worker = _worker(slow, clock, worker_id="stale")
    with pytest.raises(DeliveryLeaseLost):
        worker.dispatch_once()
    first = _delivery()
    assert first[0] == 1 and first[2] is not None
    assert first[4] is None and first[5] is None
    fresh = Publisher()
    assert _worker(fresh, clock, worker_id="replacement").dispatch_once().delivered == 1
    assert len(slow.events) == len(fresh.events) == 1
    assert str(slow.events[0].event_id) == str(fresh.events[0].event_id) == event.event_id
    later = _delivery()
    assert later[0] == 2 and later[2] is None and later[4] is not None
    assert _count("outbox_events") == 1
    assert _count("audit_records") == 1


def test_crash_after_final_publish_attempt_dead_letters_expired_lease():
    event = _event()
    clock = Clock()
    publisher = Publisher()
    worker = _worker(publisher, clock, worker_id="crashing", attempts=1)

    def crash_after_publish(claim, *, failure):
        raise OSError("injected crash after broker publish")

    worker._complete = crash_after_publish
    with pytest.raises(OSError, match="injected crash"):
        worker.dispatch_once()
    assert len(publisher.events) == 1
    assert _delivery()[0] == 1
    clock.advance(5)
    recovered = _worker(publisher, clock, worker_id="restarted", attempts=1)
    result = recovered.dispatch_once()
    assert (result.claimed, result.delivered, result.dead_lettered) == (0, 0, 1)
    state = _delivery()
    assert state[2] is None and state[5] is not None
    assert state[6] == "LEASE_EXPIRED"
    clock.advance(300)
    assert recovered.dispatch_once().claimed == 0
    assert len(publisher.events) == 1
    assert _count("outbox_events") == 1
    assert _count("audit_records") == 1
    assert publisher.events[0].event_id == __import__("uuid").UUID(event.event_id)


def test_inbox_handler_cannot_commit_partial_side_effects():
    _event()
    with psycopg.connect(ADMIN_DSN) as conn:
        row = conn.execute(
            "SELECT event_id,tenant_id,company_id,entity_id,event_type,"
            "schema_version,revision,correlation_id,recorded_at "
            "FROM company_configuration.outbox_events"
        ).fetchone()
    from pyaccountingkit.company_configuration.infrastructure.postgres.dispatch import (
        OutboxEnvelope,
    )

    event = OutboxEnvelope(*row)

    class AttemptCommit:
        def apply(self, connection, event, *, consumer_id):
            assert not hasattr(connection, "commit")
            assert not hasattr(connection, "rollback")
            assert not hasattr(connection, "transaction")
            assert not hasattr(connection, "cursor")
            CountingProjectionHandler().apply(connection, event, consumer_id=consumer_id)
            connection.commit()  # deliberately prohibited, so entire tx rolls back

    bad = PostgresInboxConsumer(
        INBOX_DSN, tenant_id="tenant-a", consumer_id="projection",
        producer_id="company-config", handler=AttemptCommit(),
    )
    with pytest.raises(AttributeError):
        bad.process(event)
    assert _count("inbox_receipts") == 0
    assert _count("inbox_projection_counts") == 0
    good = PostgresInboxConsumer(
        INBOX_DSN, tenant_id="tenant-a", consumer_id="projection",
        producer_id="company-config", handler=CountingProjectionHandler(),
    )
    assert good.process(event).applied
    assert good.process(event).duplicate
    assert _count("inbox_receipts") == 1
    assert _count("inbox_projection_counts") == 1


def test_inbox_handler_rollback_does_not_consume_receipt_or_audit():
    _event()
    with psycopg.connect(ADMIN_DSN) as conn:
        row = conn.execute(
            "SELECT event_id,tenant_id,company_id,entity_id,event_type,"
            "schema_version,revision,correlation_id,recorded_at "
            "FROM company_configuration.outbox_events"
        ).fetchone()
    from pyaccountingkit.company_configuration.infrastructure.postgres.dispatch import (
        OutboxEnvelope,
    )

    event = OutboxEnvelope(*row)

    class Exploding:
        def apply(self, connection, event, *, consumer_id):
            CountingProjectionHandler().apply(connection, event, consumer_id=consumer_id)
            raise RuntimeError("downstream projection failed")

    receiver = PostgresInboxConsumer(
        INBOX_DSN, tenant_id="tenant-a", consumer_id="projection",
        producer_id="company-config", handler=Exploding(),
    )
    with pytest.raises(RuntimeError, match="downstream"):
        receiver.process(event)
    assert _count("inbox_receipts") == 0
    assert _count("inbox_projection_counts") == 0
    assert _count("audit_records") == 1
    assert _count("outbox_events") == 1
