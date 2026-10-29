"""PostgreSQL 16: durable, least-privilege IAM revocation ACK delivery."""
# ruff: noqa: E402

import os
from uuid import uuid4

import pytest

psycopg = pytest.importorskip('psycopg')
from test_delegated_control_plane_postgres import account  # noqa: F401

from pyaccountingkit.company_configuration.infrastructure.iam.ack_delivery import (
    IamAckDeliveryWorker,
)
from pyaccountingkit.company_configuration.infrastructure.iam.http_revocation_source import (
    HttpsIamRevocationSource,
    IamHttpResponse,
)
from pyaccountingkit.company_configuration.infrastructure.iam.revocation import (
    VerifiedIamRevocation,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.iam_ack_outbox import (
    PostgresIamAckOutbox,
)
from pyaccountingkit.company_configuration.infrastructure.postgres.iam_revocation import (
    PostgresIamRevocationRepository,
)

ADMIN = os.getenv('CC_PG_ADMIN_DSN')
IAM = os.getenv('CC_PG_IAM_REVOCATION_DSN')
DELIVERY = os.getenv('CC_PG_IAM_DELIVERY_DSN')
CONTROL = os.getenv('CC_PG_CONTROL_PLANE_DSN')
RUNTIME = os.getenv('CC_PG_DSN')
AUDIT = os.getenv('CC_PG_PRIVILEGED_AUDIT_DSN')
pytestmark = pytest.mark.skipif(
    not all((ADMIN, IAM, DELIVERY, CONTROL, RUNTIME, AUDIT)),
    reason='All restricted IAM delivery SQL DSNs required',
)


def evidence(role, *, request_id=None):
    return VerifiedIamRevocation(
        event_id=uuid4(), request_id=request_id or uuid4(),
        tenant_id='tenant-a', login_role=role, operation='rotate',
        issuer='https://revocations.example.test', signer_kid='ci-kid',
        revoker_id='iam-security', signed_digest='a' * 64,
    )


def status(event_id):
    with psycopg.connect(ADMIN) as conn:
        return conn.execute(
            'SELECT state,attempts,lease_token,disposition '
            'FROM company_configuration.privileged_iam_ack_outbox '
            'WHERE event_id=%s', (event_id,),
        ).fetchone()


class Transport:
    def __init__(self, response_status=204):
        self.status = response_status
        self.calls = []

    def request(self, method, url, headers, body, timeout):
        self.calls.append((method, url, headers, body))
        return IamHttpResponse(self.status, 'application/json', b'')


def source(transport):
    return HttpsIamRevocationSource(
        origin='https://iam.example.test', bearer_token='ci-only-iam-secret',
        transport=transport,
    )


def test_sql_receipt_atomically_enqueues_ack_and_worker_delivers(request):
    role, _ = request.getfixturevalue('account')
    event = evidence(role)
    assert PostgresIamRevocationRepository(IAM).apply(event) == 'TOMBSTONED'
    assert status(event.event_id) == ('PENDING', 0, None, 'TOMBSTONED')
    transport = Transport()
    result = IamAckDeliveryWorker(
        outbox=PostgresIamAckOutbox(DELIVERY), source=source(transport),
    ).run_once(limit=1)
    assert (result.claimed, result.delivered, result.dead) == (1, 1, 0)
    assert status(event.event_id)[:3] == ('DELIVERED', 1, None)
    assert transport.calls[0][2]['Idempotency-Key'] == str(event.event_id)


def test_sql_receipt_rollback_does_not_enqueue(request):
    role, _ = request.getfixturevalue('account')
    event = evidence(role)
    try:
        with psycopg.connect(IAM) as conn:
            assert conn.execute(
                'SELECT company_configuration.cp_ack_iam_revocation('
                '%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (event.event_id, event.request_id, event.tenant_id,
                 event.login_role, event.operation, event.issuer,
                 event.signer_kid, event.revoker_id, event.signed_digest),
            ).fetchone()[0] == 'TOMBSTONED'
            raise RuntimeError('simulated process failure before SQL COMMIT')
    except RuntimeError:
        pass
    assert status(event.event_id) is None
    with psycopg.connect(ADMIN) as conn:
        assert conn.execute(
            'SELECT count(*) FROM company_configuration.privileged_iam_revocation_receipts '
            'WHERE event_id=%s', (event.event_id,),
        ).fetchone()[0] == 0


def test_failed_ack_retry_and_dead_letter_after_five_attempts(request):
    role, _ = request.getfixturevalue('account')
    event = evidence(role)
    PostgresIamRevocationRepository(IAM).apply(event)
    worker = IamAckDeliveryWorker(
        outbox=PostgresIamAckOutbox(DELIVERY), source=source(Transport(503)),
    )
    for attempt in range(1, 6):
        outcome = worker.run_once(limit=1)
        assert outcome.claimed == 1 and outcome.delivered == 0
        assert status(event.event_id)[1] == attempt
        assert status(event.event_id)[0] == ('DEAD' if attempt == 5 else 'RETRY')
        if attempt < 5:
            # Test-only time advance, never exposed to the delivery SQL role.
            with psycopg.connect(ADMIN) as conn:
                conn.execute(
                    'UPDATE company_configuration.privileged_iam_ack_outbox '
                    'SET next_attempt_at=clock_timestamp()-interval \'1 second\' '
                    'WHERE event_id=%s', (event.event_id,),
                )
    assert worker.run_once(limit=1).claimed == 0


def test_expired_lease_reclaimed_and_stale_completion_refused(request):
    role, _ = request.getfixturevalue('account')
    event = evidence(role)
    PostgresIamRevocationRepository(IAM).apply(event)
    repo = PostgresIamAckOutbox(DELIVERY)
    first = repo.claim(1)[0]
    with psycopg.connect(ADMIN) as conn:
        conn.execute(
            'UPDATE company_configuration.privileged_iam_ack_outbox '
            'SET lease_until=clock_timestamp()-interval \'1 second\' '
            'WHERE event_id=%s', (event.event_id,),
        )
    second = repo.claim(1)[0]
    assert second.lease_token != first.lease_token
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        repo.delivered(first)
    repo.delivered(second)
    assert status(event.event_id)[0] == 'DELIVERED'


def test_dedicated_delivery_login_cannot_ack_as_iam_or_read_tables(request):
    role, _ = request.getfixturevalue('account')
    event = evidence(role)
    for dsn in (RUNTIME, CONTROL, IAM, AUDIT):
        with psycopg.connect(dsn) as conn:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute('SELECT * FROM company_configuration.cp_claim_iam_ack(1)')
    with psycopg.connect(DELIVERY) as conn:
        assert conn.execute(
            'SELECT session_user,rolsuper,rolcreaterole,rolbypassrls '
            'FROM pg_roles WHERE rolname=session_user'
        ).fetchone() == ('cc_iam_delivery', False, False, False)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                'SELECT * FROM company_configuration.privileged_iam_ack_outbox'
            )
    with psycopg.connect(DELIVERY) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                'SELECT company_configuration.cp_ack_iam_revocation('
                '%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (event.event_id, event.request_id, event.tenant_id,
                 event.login_role, event.operation, event.issuer,
                 event.signer_kid, event.revoker_id, event.signed_digest),
            )


def test_two_competing_sql_workers_cannot_claim_same_receipt(request):
    role, _ = request.getfixturevalue('account')
    event = evidence(role)
    PostgresIamRevocationRepository(IAM).apply(event)
    first = PostgresIamAckOutbox(DELIVERY).claim(1)
    second = PostgresIamAckOutbox(DELIVERY).claim(1)
    assert len(first) == 1 and second == ()
    PostgresIamAckOutbox(DELIVERY).delivered(first[0])
    assert status(event.event_id)[0] == 'DELIVERED'
