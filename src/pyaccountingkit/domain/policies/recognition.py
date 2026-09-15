"""Recognition policy domain (LOT-12).

Recognition answers ``should this event be booked?`` and ``when?``
(spec sections 19-22).  It is deliberately separated from measurement
(ADR-POL-003) to keep each concern independently resolvable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any

from pyaccountingkit.core.identifiers import EntityId
from pyaccountingkit.domain.policies.applicability import PolicyContext
from pyaccountingkit.domain.policies.policy_set import PolicyType


class RecognitionState(StrEnum):
    """Possible outcomes of a recognition evaluation (spec section 22)."""

    RECOGNIZED = "RECOGNIZED"
    NOT_RECOGNIZED = "NOT_RECOGNIZED"
    DEFERRED = "DEFERRED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


@dataclass(frozen=True, slots=True)
class AccountingEvent:
    """Minimal event description consumed by a recognition policy.

    This definition intentionally remains subledger-agnostic; the detailed
    event model will be defined in the subledgers spec.
    """

    event_id: str
    accounting_entity_id: EntityId
    event_type: str
    source: str
    source_reference: str
    facts: Mapping[str, Any] = field(default_factory=dict)
    occurred_at: date | None = None
    document_date: date | None = None
    accounting_date: date | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("event_id", self.event_id),
            ("event_type", self.event_type),
            ("source", self.source),
            ("source_reference", self.source_reference),
        ):
            if not value:
                raise ValueError(f"AccountingEvent.{name} must be non-empty")


@dataclass(frozen=True, slots=True)
class RecognitionDecision:
    """Explicit result of a recognition evaluation (spec section 21).

    A decision answers whether an event is bookable and carries the
    minimal trace required for replay (ADR-POL-012).
    """

    recognized: bool
    state: RecognitionState
    recognition_date: date | None = None
    accounting_category: str | None = None
    rationale: str = ""
    evidence: tuple[str, ...] = ()
    policy_id: str = ""
    policy_version: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.recognized and self.state is RecognitionState.NOT_RECOGNIZED:
            raise ValueError("state cannot be NOT_RECOGNIZED when recognized is True")


class RecognitionPolicy(ABC):
    """Abstract base of every recognition policy (ADR-POL-003/007).

    A coded policy evaluates an event deterministically without mutating
    the ledger (ADR-POL-007).
    """

    policy_id: str
    policy_version: str
    policy_type: PolicyType = PolicyType.RECOGNITION

    @abstractmethod
    def evaluate(
        self,
        *,
        event: AccountingEvent,
        context: PolicyContext,
    ) -> RecognitionDecision:
        """Evaluate whether an economic event should be recognized."""


__all__ = [
    "AccountingEvent",
    "RecognitionDecision",
    "RecognitionPolicy",
    "RecognitionState",
]
