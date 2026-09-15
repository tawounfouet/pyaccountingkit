"""Policy applicability and resolution context (LOT-12)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pyaccountingkit.core.identifiers import EntityId


@dataclass(frozen=True, slots=True)
class PolicyApplicability:
    """Criteria a policy binding declares about when it applies."""

    standard_id: str | None = None
    edition: str | None = None
    jurisdiction: str | None = None
    sector: str | None = None
    accounting_entity_id: EntityId | None = None
    account_type: str | None = None
    reference_concept_id: str | None = None
    asset_category: str | None = None
    liability_category: str | None = None
    transaction_type: str | None = None
    journal_type: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None

    def matches(self, context: PolicyContext) -> bool:
        """Return whether context satisfies every declared criterion, fail-closed."""
        declared = (
            (self.standard_id, context.standard_id),
            (self.edition, context.edition),
            (self.jurisdiction, context.jurisdiction),
            (self.sector, context.sector),
            (self.accounting_entity_id, context.accounting_entity_id),
            (self.account_type, context.account_type),
            (self.reference_concept_id, context.reference_concept_id),
            (self.asset_category, context.asset_category),
            (self.liability_category, context.liability_category),
            (self.transaction_type, context.transaction_type),
            (self.journal_type, context.journal_type),
        )
        for expected, actual in declared:
            if expected is not None and actual != expected:
                return False
        if self.effective_from is not None and context.accounting_date < self.effective_from:
            return False
        if self.effective_to is not None and context.accounting_date > self.effective_to:
            return False
        return True

    @property
    def specificity(self) -> int:
        criteria = (
            self.standard_id,
            self.edition,
            self.jurisdiction,
            self.sector,
            self.accounting_entity_id,
            self.account_type,
            self.reference_concept_id,
            self.asset_category,
            self.liability_category,
            self.transaction_type,
            self.journal_type,
        )
        return sum(1 for criterion in criteria if criterion is not None)


@dataclass(frozen=True, slots=True)
class PolicyContext:
    """Immutable input of a policy resolution request."""

    accounting_entity_id: EntityId
    accounting_date: date
    standard_id: str | None = None
    edition: str | None = None
    jurisdiction: str | None = None
    sector: str | None = None
    reference_snapshot_id: str | None = None
    accounting_item_type: str | None = None
    account_id: str | None = None
    reference_concept_id: str | None = None
    transaction_type: str | None = None
    account_type: str | None = None
    asset_category: str | None = None
    liability_category: str | None = None
    journal_type: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


__all__ = ["PolicyApplicability", "PolicyContext"]
