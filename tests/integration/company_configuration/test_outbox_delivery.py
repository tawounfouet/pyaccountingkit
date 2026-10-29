"""PostgreSQL 16 proofs for L02-03. Requires dedicated runtime and dispatcher roles."""

import os
from datetime import UTC, datetime, timedelta
from threading import Barrier, Thread

import pytest

psycopg = pytest.importorskip("psycopg")

from test_postgres_uow import build_service, create, rename  # noqa: E402

from pyaccountingkit.company_configuration.application.service import (  # noqa: E402
    LegalEntityService,
    PermissionDenied,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.adapter import (  # noqa: E402
    PostgresUnitOfWork,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.denials import (  # noqa: E402
    PostgresDenialAudit,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.dispatch import (  # noqa: E402
    DeliveryLeaseLost,
    PostgresOutboxDispatcher,
)

ADMIN_DSN = os.getenv("CC_PG_ADMIN_DSN")
APP_DSN = os.getenv("CC_PG_DSN")
DISPATCH_DSN = os.getenv("CC_PG_DISPATCH_DSN")
DISPATCH_DSN_B = os.getenv("CC_PG_DISPATCH_DSN_B")
pytestmark = pytest.mark.skipif(
    not (ADMIN_DSN and APP_DSN and DISPATCH_DSN),
    reason="L02-03 DB proofs require admin/runtime/dispatcher test DSNs",
)


class Clock:
    def __init__(self):
        self.value = datetime.now(UTC) + timedelta(days=1)

    def now(self):
        return self.value

    def advance(self, *, seconds):
        self.value += timedelta(seconds=seconds)


class CollectingPublisher:
    def __init__(self, failures=0):
        self.events = []
        self.failures = failures

    def publish(self, event):
        self.events.append(event)
        if self.failures:
            self.failures -= 1
            raise ConnectionError("PRIVATE_TOKEN_SHOULD_NOT_BE_LOGGED")


@pytest.fixture(autouse=True)
def clean_tables():
    if not (ADMIN_DSN and APP_DSN and DISPATCH_DSN):
        yield
        return
    with psycopg.connect(ADMIN_DSN) as conn:
        conn.execute(
            "TRUNCATE company_configuration.authorization_denials, "
            "company_configuration.outbox_delivery, "
            "company_configuration.legal_entities, "
            "company_configuration.idempotency_requests, "
            "company_configuration.audit_records, "
            "company_configuration.outbox_events CASCADE"
        )
    yield


def make_dispatcher(tenant, publisher, clock=None, *, attempts=3, worker="worker-1"):
    clock = clock or Clock()
    return PostgresOutboxDispatcher(
        DISPATCH_DSN_B if tenant == "tenant-b" else DISPATCH_DSN,
        tenant_id=tenant, worker_id=worker, publisher=publisher,
        clock=clock.now, retry_seconds=2, lease_seconds=4, max_attempts=attempts,
    )


def test_delivers_once_in_normal_run_and_marks_state():
    scope, actor, _, service = build_service()
    first = service.create(create(scope), principal=actor)
    second = service.rename(rename(scope), principal=actor)
    publisher = CollectingPublisher()
    dispatcher = make_dispatcher(scope.tenant_id, publisher)
    assert dispatcher.dispatch_once(limit=10).delivered == 2
    assert dispatcher.dispatch_once().claimed == 0
    assert {str(e.event_id) for e in publisher.events} == {
        first.event_id, second.event_id,
    }
    with psycopg.connect(ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.outbox_delivery "
            "WHERE delivered_at IS NOT NULL"
        ).fetchone()[0] == 2
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.outbox_events"
        ).fetchone()[0] == 2


def test_transient_failure_retries_without_losing_original_event():
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    clock = Clock()
    publisher = CollectingPublisher(failures=1)
    dispatcher = make_dispatcher(scope.tenant_id, publisher, clock)
    first = dispatcher.dispatch_once()
    assert (first.claimed, first.retryable_failures, first.delivered) == (1, 1, 0)
    assert dispatcher.dispatch_once().claimed == 0
    clock.advance(seconds=3)
    second = dispatcher.dispatch_once()
    assert (second.delivered, second.dead_lettered) == (1, 0)
    assert len(publisher.events) == 2
    assert publisher.events[0].event_id == publisher.events[1].event_id
    with psycopg.connect(ADMIN_DSN) as conn:
        row = conn.execute(
            "SELECT attempts, delivered_at, last_error FROM "
            "company_configuration.outbox_delivery"
        ).fetchone()
        assert row[0] == 2 and row[1] is not None
        assert row[2] is None  # success clears previous error


def test_dead_letter_exhausts_attempt_limit_without_republish():
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    clock = Clock()
    publisher = CollectingPublisher(failures=5)
    dispatcher = make_dispatcher(scope.tenant_id, publisher, clock, attempts=2)
    assert dispatcher.dispatch_once().retryable_failures == 1
    clock.advance(seconds=5)
    result = dispatcher.dispatch_once()
    assert result.dead_lettered == 1
    clock.advance(seconds=500)
    assert dispatcher.dispatch_once().claimed == 0
    with psycopg.connect(ADMIN_DSN) as conn:
        row = conn.execute(
            "SELECT attempts, dead_letter_at, last_error FROM "
            "company_configuration.outbox_delivery"
        ).fetchone()
        assert row[0] == 2 and row[1] is not None
        assert row[2] == "ConnectionError"  # do not persist exception secrets


def test_lost_ack_can_redeliver_same_event_id_after_lease():
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    clock = Clock()
    publisher = CollectingPublisher()
    dispatcher = make_dispatcher(scope.tenant_id, publisher, clock)
    original_complete = dispatcher._complete

    def fail_after_publish(claim, *, failure):
        if failure is None:
            raise OSError("crash before acknowledging delivery")
        return original_complete(claim, failure=failure)

    dispatcher._complete = fail_after_publish
    with pytest.raises(OSError, match="crash before"):
        dispatcher.dispatch_once()
    clock.advance(seconds=10)
    restarted = make_dispatcher(scope.tenant_id, publisher, clock, worker="worker-2")
    assert restarted.dispatch_once().delivered == 1
    assert len(publisher.events) == 2
    assert publisher.events[0].event_id == publisher.events[1].event_id


def test_parallel_workers_claim_one_pending_event_once():
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    publisher = CollectingPublisher()
    barrier = Barrier(3)
    outcomes = []

    def worker(worker_id):
        dispatcher = make_dispatcher(scope.tenant_id, publisher, worker=worker_id)
        barrier.wait()
        outcomes.append(dispatcher.dispatch_once().delivered)

    threads = [Thread(target=worker, args=(name,)) for name in ("alpha", "beta")]
    for t in threads:
        t.start()
    barrier.wait()
    for t in threads:
        t.join(timeout=10)
    assert sorted(outcomes) == [0, 1]
    assert len(publisher.events) == 1


def test_dispatcher_only_reads_selected_tenant():
    a, actor_a, _, svc_a = build_service(tenant="tenant-a")
    b, actor_b, _, svc_b = build_service(tenant="tenant-b")
    svc_a.create(create(a), principal=actor_a)
    svc_b.create(create(b), principal=actor_b)
    publisher = CollectingPublisher()
    assert make_dispatcher(a.tenant_id, publisher).dispatch_once().delivered == 1
    assert publisher.events[0].tenant_id == a.tenant_id
    with psycopg.connect(ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.outbox_events"
        ).fetchone()[0] == 2


def test_verified_denials_audited_with_authoritative_tenant_only():
    scope, actor, auth, _ = build_service()
    sink = PostgresDenialAudit(APP_DSN)
    service = LegalEntityService(lambda: PostgresUnitOfWork(APP_DSN), auth, denial_audit=sink)
    with pytest.raises(PermissionDenied):
        # Authenticated actor tenant-a cannot submit a tenant-b scope.
        foreign_scope, _, _, _ = build_service(tenant="tenant-b")
        service.read(principal=actor, scope=foreign_scope)
    auth.revoke(actor_id=actor.actor_id, action="legal_entity.create", scope=scope)
    with pytest.raises(PermissionDenied):
        service.create(create(scope), principal=actor)
    with psycopg.connect(ADMIN_DSN) as conn:
        rows = conn.execute(
            "SELECT tenant_id, actor_id, reason_code FROM "
            "company_configuration.authorization_denials ORDER BY recorded_at"
        ).fetchall()
        assert {row[2] for row in rows} == {"TENANT_MISMATCH", "PERMISSION_DENIED"}
        assert all(r[0] == actor.tenant_id and r[1] == actor.actor_id for r in rows)
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.legal_entities"
        ).fetchone()[0] == 0
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "DELETE FROM company_configuration.authorization_denials"
            )


def test_denial_audit_failure_never_allows_a_forbidden_command():
    scope, actor, auth, _ = build_service()

    class FailingSink:
        def record_denial(self, **kwargs):
            raise OSError("audit storage unavailable")

    auth.revoke(actor_id=actor.actor_id, action="legal_entity.create", scope=scope)
    service = LegalEntityService(
        lambda: PostgresUnitOfWork(APP_DSN), auth, denial_audit=FailingSink()
    )
    with pytest.raises(OSError, match="audit storage unavailable"):
        service.create(create(scope), principal=actor)
    with psycopg.connect(ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.legal_entities"
        ).fetchone()[0] == 0


def test_expired_delivery_lease_cannot_ack_even_without_competing_worker():
    """A stale ack must fail even before the next claim fences its token."""
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    clock = Clock()
    publisher = CollectingPublisher()
    old_worker = make_dispatcher(scope.tenant_id, publisher, clock)
    claims = old_worker._claim(1)
    assert len(claims) == 1
    clock.advance(seconds=5)  # lease_seconds=4
    with pytest.raises(DeliveryLeaseLost, match="Lost outbox lease"):
        old_worker._complete(claims[0], failure=None)
    with psycopg.connect(ADMIN_DSN) as conn:
        row = conn.execute(
            "SELECT attempts,delivered_at,dead_letter_at "
            "FROM company_configuration.outbox_delivery"
        ).fetchone()
        assert row == (1, None, None)
    restarted = make_dispatcher(
        scope.tenant_id, publisher, clock, worker="new-worker",
    )
    assert restarted.dispatch_once().delivered == 1
    with psycopg.connect(ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT attempts,delivered_at IS NOT NULL "
            "FROM company_configuration.outbox_delivery"
        ).fetchone() == (2, True)


def test_final_attempt_crash_is_dead_lettered_without_extra_publish():
    """A publisher succeeded before the final lease expired; no extra attempt."""
    scope, actor, _, service = build_service()
    created = service.create(create(scope), principal=actor)
    clock = Clock()
    publisher = CollectingPublisher()
    first = make_dispatcher(scope.tenant_id, publisher, clock, attempts=1)
    claim = first._claim(1)
    assert len(claim) == 1 and claim[0].attempts == 1
    publisher.publish(claim[0].event)  # external side effect succeeded
    # Process dies before calling _complete; no ack or failure transition.
    clock.advance(seconds=5)
    restarted = make_dispatcher(
        scope.tenant_id, publisher, clock, attempts=1, worker="restart",
    )
    assert restarted.dispatch_once().claimed == 0
    assert len(publisher.events) == 1
    assert str(publisher.events[0].event_id) == created.event_id
    with psycopg.connect(ADMIN_DSN) as conn:
        delivery = conn.execute(
            "SELECT attempts,dead_letter_at IS NOT NULL,delivered_at,"
            "lease_owner,lease_token,lease_until,last_error "
            "FROM company_configuration.outbox_delivery"
        ).fetchone()
        assert delivery == (1, True, None, None, None, None, "LEASE_EXPIRED")
        assert conn.execute(
            "SELECT count(*) FROM company_configuration.outbox_events"
        ).fetchone()[0] == 1
    clock.advance(seconds=500)
    assert restarted.dispatch_once().claimed == 0


def test_expired_last_lease_not_dead_lettered_until_it_actually_expires():
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    clock = Clock()
    publisher = CollectingPublisher()
    worker = make_dispatcher(scope.tenant_id, publisher, clock, attempts=1)
    claim = worker._claim(1)
    assert len(claim) == 1
    assert worker.dispatch_once().claimed == 0
    with psycopg.connect(ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT dead_letter_at,attempts FROM "
            "company_configuration.outbox_delivery"
        ).fetchone() == (None, 1)
    # The legitimately leased worker can still finish before the deadline.
    assert not worker._complete(claim[0], failure=None)
    with psycopg.connect(ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT delivered_at IS NOT NULL,dead_letter_at FROM "
            "company_configuration.outbox_delivery"
        ).fetchone() == (True, None)


def test_exhausted_unleased_attempt_cannot_be_reclaimed():
    """A previously committed max attempts without a lease also fails shut."""
    scope, actor, _, service = build_service()
    service.create(create(scope), principal=actor)
    clock = Clock()
    publisher = CollectingPublisher()
    worker = make_dispatcher(scope.tenant_id, publisher, clock, attempts=2)
    with psycopg.connect(ADMIN_DSN) as conn:
        conn.execute(
            "INSERT INTO company_configuration.outbox_delivery "
            "(tenant_id,event_id,attempts,available_at) "
            "SELECT tenant_id,event_id,2,clock_timestamp() "
            "FROM company_configuration.outbox_events"
        )
    assert worker.dispatch_once().claimed == 0
    assert publisher.events == []
    with psycopg.connect(ADMIN_DSN) as conn:
        assert conn.execute(
            "SELECT attempts,dead_letter_at IS NOT NULL,last_error "
            "FROM company_configuration.outbox_delivery"
        ).fetchone() == (2, True, "LEASE_EXPIRED")
