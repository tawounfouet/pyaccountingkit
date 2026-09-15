"""Reproducibility envelope foundation — seals a computation's inputs & output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pyaccountingkit.domain.traceability.trace import CanonicalHasher, TraceContext


@dataclass(frozen=True, slots=True)
class ReproducibilityEnvelope:
    """Locks a run against the inputs, program version and output hash."""

    trace_id: str
    inputs_hash: str
    output_hash: str
    control_versions: dict[str, int]
    created_at: datetime

    @classmethod
    def seal(
        cls,
        trace: TraceContext,
        inputs: dict[str, Any],
        output: dict[str, Any],
        control_versions: dict[str, int],
        created_at: datetime,
    ) -> ReproducibilityEnvelope:
        return cls(
            trace_id=trace.trace_id,
            inputs_hash=CanonicalHasher.digest(inputs),
            output_hash=CanonicalHasher.digest(output),
            control_versions=dict(control_versions),
            created_at=created_at,
        )


__all__ = ["ReproducibilityEnvelope"]
