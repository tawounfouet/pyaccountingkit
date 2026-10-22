"""Audit events — the serializable record of business mutations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

from pyaccountingkit.core.immutable_json import freeze_json_mapping


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable, JSON-serializable audit trail entry."""

    event_type: str
    entity_id: str
    actor_id: str
    occurred_at: datetime
    payload: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", freeze_json_mapping(self.payload))


__all__ = ["AuditEvent"]
