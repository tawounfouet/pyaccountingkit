"""Policy execution trace — immutable record of every policy run (LOT-12).

Every evaluation of a recognition / measurement / closing policy emits a
``PolicyExecutionTrace``.  Traces are immutable (ADR-POL-012) and must
survive version changes to support replay (ADR-POL-016/017, spec section 81).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from pyaccountingkit.domain.policies.policy_set import PolicyType


@dataclass(frozen=True, slots=True)
class PolicyExecutionTrace:
    """Immutable audit record of one policy evaluation (ADR-POL-012)."""

    trace_id: str
    policy_type: PolicyType
    policy_id: str
    policy_version: str
    policy_set_id: str
    policy_set_version: str
    accounting_entity_id: str
    accounting_date: date
    reference_snapshot_id: str | None = None
    inputs: Mapping[str, Any] = field(default_factory=dict)
    evaluated_at: datetime | None = None
    outcome: str = ""

    def __post_init__(self) -> None:
        for name, value in (
            ("trace_id", self.trace_id),
            ("policy_id", self.policy_id),
            ("policy_version", self.policy_version),
            ("policy_set_id", self.policy_set_id),
            ("policy_set_version", self.policy_set_version),
            ("accounting_entity_id", self.accounting_entity_id),
        ):
            if not value:
                raise ValueError(f"PolicyExecutionTrace.{name} must be non-empty")


@dataclass(frozen=True, slots=True)
class PolicyResolutionRecord:
    """Immutable snapshot of a resolution run, embedded in a trace."""

    policy_type: PolicyType
    selected_policy_id: str
    selected_policy_version: str
    context_standard_id: str | None = None
    context_entity_id: str | None = None
    context_date: date | None = None


__all__ = [
    "PolicyExecutionTrace",
    "PolicyResolutionRecord",
]
