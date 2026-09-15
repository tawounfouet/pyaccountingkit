"""Provenance — where a business fact came from (distinct from audit).

Audit records *what happened*; provenance records *where the fact came
from* (system, user, import).  Both are append-only but play different
roles (DoD `provenance distinct from audit`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ProvenanceSource(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    IMPORT = "IMPORT"
    MIGRATION = "MIGRATION"


@dataclass(frozen=True, slots=True)
class ProvenanceRef:
    """Immutable declaration of the origin of one entity/fact."""

    entity_id: str
    source: ProvenanceSource
    source_id: str
    actor_id: str
    recorded_at: datetime


__all__ = ["ProvenanceRef", "ProvenanceSource"]
