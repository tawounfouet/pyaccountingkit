"""Impairment policy domain (LOT-13, foundation).

An ``ImpairmentPolicy`` assesses whether a carrying amount must be
written down (spec section 43-45).  The output is an
``ImpairmentDecision``; the posting of any write-down is handled by the
proposal → posting pipeline (ADR-POL-007).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pyaccountingkit.core.money import Money
from pyaccountingkit.domain.policies.policy_set import PolicyType
from pyaccountingkit.domain.policies.policy_trace import PolicyExecutionTrace


@dataclass(frozen=True, slots=True)
class ImpairmentDecision:
    """Outcome of an impairment assessment (spec section 45)."""

    impaired: bool
    carrying_amount_before: Money
    recoverable_amount: Money | None = None
    impairment_amount: Money | None = None
    carrying_amount_after: Money | None = None
    reversal_allowed: bool = False
    rationale: str = ""
    policy_trace: PolicyExecutionTrace | None = None


class ImpairmentPolicy(ABC):
    """Abstract impairment policy (spec section 44)."""

    policy_id: str = ""
    policy_version: str = ""
    policy_type: PolicyType = PolicyType.IMPAIRMENT

    @abstractmethod
    def assess(
        self,
        *,
        carrying_amount: Money,
        recoverable_amount: Money | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ImpairmentDecision:
        """Assess impairment for a subject carrying amount."""


__all__ = [
    "ImpairmentDecision",
    "ImpairmentPolicy",
]
