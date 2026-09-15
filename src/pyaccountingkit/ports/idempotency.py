"""Idempotency port — claims unique keys across a mutation boundary."""

from __future__ import annotations

from typing import Protocol


class IdempotencyStoreProtocol(Protocol):
    """Guards against replaying a mutation with the same business key."""

    def claim(self, key: str) -> bool:
        """Claim the key once; return False when already claimed."""
        ...

    def complete(self, key: str) -> None:
        """Mark a previously claimed key as successfully executed."""
        ...


__all__ = ["IdempotencyStoreProtocol"]
