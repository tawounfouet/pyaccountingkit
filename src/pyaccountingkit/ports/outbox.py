"""Outbox port — transactional messages published after a commit."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OutboxRecord:
    """A JSON-serializable message deferred until the enclosing commit."""

    event_type: str
    entity_id: str
    payload: Mapping[str, str] = field(default_factory=dict)
    idempotency_key: str = ""


class OutboxPublisherProtocol(Protocol):
    """Buffers messages that become visible only once committed."""

    def publish(self, record: OutboxRecord) -> None:
        """Stage a message for the next commit."""
        ...


__all__ = ["OutboxRecord", "OutboxPublisherProtocol"]
