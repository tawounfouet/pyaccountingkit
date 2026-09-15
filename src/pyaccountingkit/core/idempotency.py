"""Idempotency-key value objects for safe, replayable mutations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    """Canonical idempotency key derived from scope, operation and payload."""

    scope: str
    operation: str
    payload_digest: str

    def canonical(self) -> str:
        """Serialize the key to its canonical storage string."""
        return f"{self.scope}:{self.operation}:{self.payload_digest}"

    @classmethod
    def derive(cls, scope: str, operation: str, payload: bytes = b"") -> IdempotencyKey:
        """Derive a deterministic key from the operation payload.

        Identical (scope, operation, payload) triples always yield the same
        key, enabling exactly-once mutation semantics.
        """
        digest = hashlib.sha256(payload).hexdigest()
        return cls(scope=scope, operation=operation, payload_digest=digest)

    @classmethod
    def from_canonical(cls, value: str) -> IdempotencyKey:
        """Parse a canonical string back into an ``IdempotencyKey``."""
        scope, _, remainder = value.partition(":")
        operation, _, digest = remainder.partition(":")
        if not scope or not operation or not digest:
            raise ValueError(f"Malformed idempotency key: {value!r}")
        if len(digest) != 64:
            raise ValueError(f"Malformed idempotency key (digest): {value!r}")
        try:
            int(digest, 16)
        except ValueError as exc:
            raise ValueError(f"Malformed idempotency key (digest): {value!r}") from exc
        return cls(scope=scope, operation=operation, payload_digest=digest)

    def __str__(self) -> str:
        return self.canonical()


__all__ = ["IdempotencyKey"]
