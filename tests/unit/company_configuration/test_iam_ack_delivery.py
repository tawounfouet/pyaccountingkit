"""L02-07k: HTTPS connector contract and bounded ack worker failure modes."""

import json
from uuid import uuid4

import pytest

from pyaccountingkit.company_configuration.infrastructure.iam.ack_delivery import (
    IamAckDeliveryWorker,
)
from pyaccountingkit.company_configuration.infrastructure.iam.http_revocation_source import (
    HttpsIamRevocationSource,
    IamHttpResponse,
    IamHttpUnavailable,
)
from pyaccountingkit.company_configuration.infrastructure.iam.revocation import (
    IamRevocationReceipt,
)


class FakeHttp:
    def __init__(self, response):
        self.response = response
        self.calls = []
        self.fail = False

    def request(self, method, url, headers, body, timeout):
        self.calls.append((method, url, headers, body, timeout))
        if self.fail:
            raise OSError('No route to provider')
        return self.response


class Lease:
    def __init__(self, receipt):
        self.receipt = receipt


class Repo:
    def __init__(self, receipts=()):
        self.receipts = list(receipts)
        self.delivered_rows = []
        self.failed_rows = []
        self.failure_result = 'RETRY'

    def claim(self, limit):
        result = self.receipts[:limit]
        self.receipts = self.receipts[limit:]
        return tuple(Lease(r) for r in result)

    def delivered(self, lease):
        self.delivered_rows.append(lease.receipt)

    def failed(self, lease, error):
        self.failed_rows.append((lease.receipt, error))
        return self.failure_result


def _receipt():
    return IamRevocationReceipt(uuid4(), uuid4(), 'tenant-a', 'REVOKED')


def test_get_uses_pinned_origin_and_returns_compact_signed_evidence():
    http = FakeHttp(IamHttpResponse(200, 'application/jose', b'header.payload.signature'))
    src = HttpsIamRevocationSource(
        origin='https://iam.example.test', bearer_token='secret-do-not-print',
        transport=http,
    )
    event = uuid4()
    assert src.read(event) == 'header.payload.signature'
    method, url, headers, data, timeout = http.calls[0]
    assert (method, url, data, timeout) == (
        'GET', f'https://iam.example.test/v1/revocations/{event}', None, 5.0,
    )
    assert headers['Authorization'] == 'Bearer secret-do-not-print'
    assert 'secret-do-not-print' not in repr(src)


def test_post_is_idempotent_and_never_invents_successful_prevention():
    http = FakeHttp(IamHttpResponse(202, 'application/json', b''))
    source = HttpsIamRevocationSource(
        origin='https://iam.example.test', bearer_token='super-private', transport=http,
    )
    receipt = IamRevocationReceipt(uuid4(), uuid4(), 'tenant-a', 'ALREADY_CONSUMED')
    source.acknowledge(receipt)
    method, url, headers, payload, _ = http.calls[0]
    assert method == 'POST' and url.endswith(f'{receipt.event_id}/acknowledgements')
    assert headers['Idempotency-Key'] == str(receipt.event_id)
    assert json.loads(payload)['disposition'] == 'ALREADY_CONSUMED'
    assert 'super-private' not in repr(source)


@pytest.mark.parametrize('origin', [
    'http://iam.example.test', 'https://localhost',
    'https://username:pwd@iam.example.test', 'https://iam.example.test/path',
    'https://iam.example.test?url=evil', 'file:///tmp/a',
])
def test_untrusted_http_origin_denied(origin):
    with pytest.raises(ValueError):
        HttpsIamRevocationSource(origin=origin, bearer_token='secret')


@pytest.mark.parametrize('result', [
    IamHttpResponse(301, 'application/jose', b'header.payload.signature'),
    IamHttpResponse(200, 'text/plain', b'header.payload.signature'),
    IamHttpResponse(200, 'application/jose', b'a' * 8193),
    IamHttpResponse(404, 'application/jose', b'header.payload.signature'),
])
def test_unsigned_or_unsafe_http_response_denied(result):
    source = HttpsIamRevocationSource(
        origin='https://iam.example.test', bearer_token='secret',
        transport=FakeHttp(result),
    )
    with pytest.raises(IamHttpUnavailable):
        source.read(uuid4())


def test_failed_http_ack_never_marks_sql_delivered():
    receipt = _receipt()
    repo = Repo((receipt,))
    transport = FakeHttp(IamHttpResponse(503, 'application/json', b''))
    source = HttpsIamRevocationSource(
        origin='https://iam.example.test', bearer_token='private', transport=transport,
    )
    outcome = IamAckDeliveryWorker(outbox=repo, source=source).run_once()
    assert (outcome.claimed, outcome.delivered, outcome.retry) == (1, 0, 1)
    assert repo.delivered_rows == []
    assert repo.failed_rows == [(receipt, 'NETWORK_ERROR')]


def test_worker_success_and_dead_letter_accounting():
    receipt = _receipt()
    repo = Repo((receipt,))
    src = HttpsIamRevocationSource(
        origin='https://iam.example.test', bearer_token='secret',
        transport=FakeHttp(IamHttpResponse(204, 'application/json', b'')),
    )
    success = IamAckDeliveryWorker(outbox=repo, source=src).run_once(limit=1)
    assert (success.delivered, success.retry, success.dead) == (1, 0, 0)
    assert repo.delivered_rows == [receipt]
    repo = Repo((receipt,))
    repo.failure_result = 'DEAD'
    src = HttpsIamRevocationSource(
        origin='https://iam.example.test', bearer_token='secret',
        transport=FakeHttp(IamHttpResponse(403, 'application/json', b'')),
    )
    result = IamAckDeliveryWorker(outbox=repo, source=src).run_once()
    assert result.dead == 1 and result.delivered == 0


def test_worker_rejects_unbounded_fetch():
    with pytest.raises(ValueError):
        IamAckDeliveryWorker(outbox=object(), source=object())
    with pytest.raises(ValueError):
        IamAckDeliveryWorker(outbox=Repo(), source=object())
    class Source:
        def acknowledge(self, receipt):
            pass
    with pytest.raises(ValueError):
        IamAckDeliveryWorker(outbox=Repo(), source=Source()).run_once(limit=200)
