"""Audit events — the serializable record of business mutations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable, JSON-serializable audit trail entry."""

    event_type: str
    entity_id: str
    actor_id: str
    occurred_at: datetime
    payload: Mapping[str, str] = field(default_factory=dict)


__all__ = ["AuditEvent"]
