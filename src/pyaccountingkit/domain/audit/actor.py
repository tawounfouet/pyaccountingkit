"""Actor context used by audit and traceability."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActorContext:
    """Who performed a mutation (user or system)."""

    user_id: str


__all__ = ["ActorContext"]
