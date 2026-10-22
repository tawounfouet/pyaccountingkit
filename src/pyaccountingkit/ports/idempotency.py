"""Idempotency port — claims unique keys across a mutation boundary."""

from __future__ import annotations

from typing import Protocol


class IdempotencyStoreProtocol(Protocol):
    """Guards against replaying a mutation with the same business key."""

    def claim(self, key: str, payload_fingerprint: str = "") -> bool:
        """Claim the key once.

        Return False only when the same key is already bound to the same
        semantic payload. Reusing a key with a different fingerprint must
        fail with IdempotencyConflictError.
        """
        ...

    def complete(self, key: str) -> None:
        """Mark a previously claimed key as successfully executed."""
        ...


__all__ = ["IdempotencyStoreProtocol"]
