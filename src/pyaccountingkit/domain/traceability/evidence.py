"""Evidence — verifiable material captured by a control run."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Evidence:
    """A checksum-sealed artifact linked to a control run."""

    id: str
    control_run_id: str
    capsule: str
    checksum: str
    captured_at: datetime


__all__ = ["Evidence"]
