"""Concrete HTTPS transport for the versioned PyAccountingKit IAM revocation API.

This adapter defines a provider contract, not a vendor-certified integration.
URLs are deployment-pinned, never derived from a JWS/header/provider response.
"""

import json
import ssl
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
from uuid import UUID

from .revocation import IamRevocationReceipt


class IamHttpUnavailable(ConnectionError):
    """HTTP provider did not complete the requested operation."""


@dataclass(frozen=True, slots=True)
class IamHttpResponse:
    status: int
    content_type: str
    body: bytes


class IamHttpTransport(Protocol):
    def request(
        self, method: str, url: str, headers: dict[str, str],
        body: bytes | None, timeout: float,
    ) -> IamHttpResponse: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HttpsIamTransport:
    """Standard-library HTTPS with CA and hostname verification, no redirects."""

    def __init__(self) -> None:
        self._opener = build_opener(
            HTTPSHandler(context=ssl.create_default_context()), _NoRedirect()
        )

    def request(
        self, method: str, url: str, headers: dict[str, str],
        body: bytes | None, timeout: float,
    ) -> IamHttpResponse:
        try:
            req = Request(url, headers=headers, method=method, data=body)
            with self._opener.open(req, timeout=timeout) as response:
                size = response.headers.get('Content-Length')
                if size is not None and int(size) > 8192:
                    raise IamHttpUnavailable('IAM response exceeds size limit')
                content = response.read(8193)
                if len(content) > 8192:
                    raise IamHttpUnavailable('IAM response exceeds size limit')
                return IamHttpResponse(
                    response.status, response.headers.get_content_type(), content
                )
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            raise IamHttpUnavailable('IAM HTTPS transport failed') from exc


class HttpsIamRevocationSource:
    """Fetch compact JWS and POST idempotent delivery receipt over HTTPS.

    Provider contract (both endpoints under the pinned origin):
      GET /v1/revocations/{event-uuid} -> 200 application/jose compact JWS
      POST /v1/revocations/{event-uuid}/acknowledgements -> 2xx
      Idempotency-Key: event UUID (upstream MUST deduplicate this value)
    """

    def __init__(
        self, *, origin: str, bearer_token: str, timeout: float = 5.0,
        transport: IamHttpTransport | None = None,
    ) -> None:
        target = urlsplit(origin)
        if (
            target.scheme != 'https' or not target.hostname
            or target.path not in ('', '/') or target.query or target.fragment
            or target.username or target.password or '\\' in origin
            or target.hostname in ('localhost', '127.0.0.1', '::1')
        ):
            raise ValueError('Pinned HTTPS IAM origin required')
        if not isinstance(bearer_token, str) or not bearer_token.strip():
            raise ValueError('Explicit IAM service credential required')
        if '\n' in bearer_token or '\r' in bearer_token:
            raise ValueError('Invalid service credential')
        if not 0.1 <= timeout <= 15.0:
            raise ValueError('Bounded IAM timeout required')
        self._origin = origin.rstrip('/')
        self._token = bearer_token
        self._timeout = timeout
        self._transport = transport if transport is not None else HttpsIamTransport()

    def __repr__(self) -> str:
        return 'HttpsIamRevocationSource(credentials=<redacted>)'

    def _request(
        self, method: str, path: str, body: bytes | None = None,
        idempotency_key: str | None = None,
    ) -> IamHttpResponse:
        headers = {
            'Authorization': 'Bearer ' + self._token,
            'Accept': 'application/jose',
            'Cache-Control': 'no-store',
        }
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if idempotency_key is not None:
            headers['Idempotency-Key'] = idempotency_key
        try:
            return self._transport.request(
                method, self._origin + path, headers, body, self._timeout
            )
        except Exception as exc:
            raise IamHttpUnavailable('IAM service request failed') from exc

    def read(self, event_id: UUID) -> str:
        if not isinstance(event_id, UUID):
            raise ValueError('Canonical IAM event UUID required')
        response = self._request('GET', f'/v1/revocations/{event_id}')
        if response.status != 200 or response.content_type not in (
            'application/jose', 'application/jwt',
        ) or not (1 <= len(response.body) <= 8192):
            raise IamHttpUnavailable('IAM signed revocation unavailable')
        try:
            return response.body.decode('ascii')
        except UnicodeDecodeError as exc:
            raise IamHttpUnavailable('IAM evidence is not compact JWS') from exc

    def acknowledge(self, receipt: IamRevocationReceipt) -> None:
        allowed = {'TOMBSTONED', 'REVOKED', 'ALREADY_REVOKED', 'ALREADY_CONSUMED'}
        if not isinstance(receipt, IamRevocationReceipt) or (
            receipt.disposition not in allowed
        ):
            raise ValueError('Exact durable IAM receipt required')
        payload = json.dumps({
            'event_id': str(receipt.event_id),
            'request_id': str(receipt.request_id),
            'tenant_id': receipt.tenant_id,
            'disposition': receipt.disposition,
        }, sort_keys=True, separators=(',', ':')).encode('utf-8')
        response = self._request(
            'POST', f'/v1/revocations/{receipt.event_id}/acknowledgements', payload,
            idempotency_key=str(receipt.event_id),
        )
        if response.status not in (200, 201, 202, 204):
            raise IamHttpUnavailable('IAM acknowledgement not accepted')
