"""Framework-neutral command context for the public API."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class CommandContext:
    """Cross-cutting context supplied by a consumer for a command."""

    actor: str
    correlation_id: str
    request_id: str | None = None
    idempotency_key: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.actor.strip():
            raise ValueError("actor must not be empty")
        if not self.correlation_id.strip():
            raise ValueError("correlation_id must not be empty")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


__all__ = ["CommandContext"]
