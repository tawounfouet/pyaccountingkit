"""Trace context and canonical hashing for reproducible runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class TraceContext:
    """One chained processing attempt across the system."""

    trace_id: str
    actor_id: str
    started_at: datetime


class CanonicalHasher:
    """Deterministic sha256 over a canonical JSON encoding.

    Dictionaries are serialized with sorted keys so that the hash of a
    structure does not depend on insertion order.
    """

    @staticmethod
    def digest(payload: dict[str, Any]) -> str:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=_json_default,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_default(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


__all__ = ["TraceContext", "CanonicalHasher"]
